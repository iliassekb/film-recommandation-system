"""
Service module for loading recommendations and movies from lakehouse.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class RecommendationsService:
    """Service to load recommendations and movies from lakehouse."""
    
    def __init__(self, lakehouse_path: str = "/lakehouse"):
        """
        Initialize the recommendations service.
        
        Args:
            lakehouse_path: Path to the lakehouse directory
        """
        self.lakehouse_path = lakehouse_path
        self.recommendations_path = os.path.join(lakehouse_path, "gold", "recommendations_als")
        self.movies_path = os.path.join(lakehouse_path, "silver", "movies")
        
        # Cache for movies (loaded once, used many times)
        self._movies_cache: Optional[pd.DataFrame] = None
        self._recommendations_cache: Optional[pd.DataFrame] = None
        
    def _load_movies(self) -> pd.DataFrame:
        """Load movies data from Silver layer."""
        if self._movies_cache is not None:
            return self._movies_cache
        
        try:
            logger.info(f"Loading movies from {self.movies_path}")
            
            # Try Delta format first, then Parquet
            if os.path.exists(self.movies_path):
                # Check if it's Delta (has _delta_log) or Parquet
                delta_log_path = os.path.join(self.movies_path, "_delta_log")
                if os.path.exists(delta_log_path):
                    # Delta format - read parquet files directly
                    parquet_files = list(Path(self.movies_path).glob("**/*.parquet"))
                    if parquet_files:
                        dfs = [pd.read_parquet(f) for f in parquet_files]
                        df = pd.concat(dfs, ignore_index=True)
                    else:
                        raise FileNotFoundError(f"No parquet files found in {self.movies_path}")
                else:
                    # Parquet format
                    df = pd.read_parquet(self.movies_path)
            else:
                raise FileNotFoundError(f"Movies path does not exist: {self.movies_path}")
            
            # Ensure movie_id is int
            if 'movie_id' in df.columns:
                df['movie_id'] = df['movie_id'].astype(int)
            
            self._movies_cache = df
            logger.info(f"Loaded {len(df)} movies")
            return df
            
        except Exception as e:
            logger.error(f"Error loading movies: {e}")
            raise
    
    def _load_recommendations(self) -> pd.DataFrame:
        """Load recommendations data from Gold layer."""
        if self._recommendations_cache is not None:
            return self._recommendations_cache
        
        try:
            logger.info(f"Loading recommendations from {self.recommendations_path}")
            
            if not os.path.exists(self.recommendations_path):
                raise FileNotFoundError(f"Recommendations path does not exist: {self.recommendations_path}")
            
            # Load all parquet files
            parquet_files = list(Path(self.recommendations_path).glob("*.parquet"))
            if not parquet_files:
                raise FileNotFoundError(f"No parquet files found in {self.recommendations_path}")
            
            # Read parquet files
            dfs = []
            for file_path in parquet_files:
                try:
                    df = pd.read_parquet(file_path)
                    dfs.append(df)
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")
                    continue
            
            if not dfs:
                raise ValueError("No valid parquet files could be read")
            
            # Combine all dataframes
            combined_df = pd.concat(dfs, ignore_index=True)
            
            # Handle different possible schemas
            # Schema 1: Flattened (user_id, movie_id, score, rank, ...)
            # Schema 2: Nested (user_id, recommendations array, ...)
            
            if 'recommendations' in combined_df.columns:
                # Schema 2: Nested structure - need to explode
                logger.info("Detected nested recommendations schema, exploding...")
                rows = []
                for _, row in combined_df.iterrows():
                    user_id = row['user_id']
                    recommendations = row['recommendations']
                    
                    # Handle different formats of recommendations
                    # Could be list, numpy array, or string
                    if hasattr(recommendations, '__iter__') and not isinstance(recommendations, (str, bytes)):
                        # Convert to list if it's a numpy array
                        if hasattr(recommendations, 'tolist'):
                            recommendations = recommendations.tolist()
                        
                        for rec in recommendations:
                            if isinstance(rec, dict):
                                rows.append({
                                    'user_id': user_id,
                                    'movie_id': rec.get('movie_id'),
                                    'score': rec.get('score', rec.get('rating', 0.0)),
                                    'rank': rec.get('rank', 0)
                                })
                    elif isinstance(recommendations, str):
                        # Try to parse as JSON
                        try:
                            recs = json.loads(recommendations)
                            for rec in recs:
                                rows.append({
                                    'user_id': user_id,
                                    'movie_id': rec.get('movie_id'),
                                    'score': rec.get('score', rec.get('rating', 0.0)),
                                    'rank': rec.get('rank', 0)
                                })
                        except:
                            pass
                
                combined_df = pd.DataFrame(rows)
            
            # Ensure user_id and movie_id are int
            if 'user_id' in combined_df.columns:
                combined_df['user_id'] = combined_df['user_id'].astype(int)
            if 'movie_id' in combined_df.columns:
                combined_df['movie_id'] = combined_df['movie_id'].astype(int)
            
            # Sort by user_id, then by rank (or score descending)
            if 'rank' in combined_df.columns:
                combined_df = combined_df.sort_values(['user_id', 'rank'])
            elif 'score' in combined_df.columns:
                combined_df = combined_df.sort_values(['user_id', 'score'], ascending=[True, False])
            
            self._recommendations_cache = combined_df
            logger.info(f"Loaded recommendations for {combined_df['user_id'].nunique()} users")
            return combined_df
            
        except Exception as e:
            logger.error(f"Error loading recommendations: {e}")
            raise
    
    def get_recommendations_for_user(
        self, 
        user_id: int, 
        limit: int = 10,
        include_movie_details: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recommendations for a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of recommendations to return
            include_movie_details: Whether to include movie details (title, genres, etc.)
        
        Returns:
            List of recommendation dictionaries
        """
        try:
            # Load recommendations
            recs_df = self._load_recommendations()
            
            # Filter by user_id
            user_recs = recs_df[recs_df['user_id'] == user_id].head(limit)
            
            if user_recs.empty:
                logger.warning(f"No recommendations found for user {user_id}")
                return []
            
            # Convert to list of dicts
            recommendations = []
            for _, row in user_recs.iterrows():
                rec = {
                    'movie_id': int(row['movie_id']),
                    'score': float(row.get('score', 0.0)),
                    'rank': int(row.get('rank', 0))
                }
                
                # Add movie details if requested
                if include_movie_details:
                    movies_df = self._load_movies()
                    movie_info = movies_df[movies_df['movie_id'] == rec['movie_id']]
                    
                    if not movie_info.empty:
                        movie_row = movie_info.iloc[0]
                        rec['title'] = movie_row.get('title', 'Unknown')
                        rec['release_year'] = int(movie_row.get('release_year', 0)) if pd.notna(movie_row.get('release_year')) else None
                        
                        # Handle genres (could be array, numpy array, or string)
                        genres = movie_row.get('genres', [])
                        if isinstance(genres, str):
                            # Pipe-separated string
                            rec['genres'] = [g.strip() for g in genres.split('|') if g.strip()]
                        elif hasattr(genres, 'tolist'):
                            # Numpy array - convert to list
                            rec['genres'] = genres.tolist()
                        elif isinstance(genres, list):
                            rec['genres'] = genres
                        else:
                            rec['genres'] = []
                    else:
                        rec['title'] = 'Unknown'
                        rec['release_year'] = None
                        rec['genres'] = []
                
                recommendations.append(rec)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            raise
    
    def clear_cache(self):
        """Clear the internal cache."""
        self._movies_cache = None
        self._recommendations_cache = None

