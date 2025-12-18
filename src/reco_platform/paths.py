"""
Path utilities - Builds bronze/silver/gold paths consistently.
"""

import os
from pathlib import Path
from typing import Optional
from .config import Config


def get_lakehouse_base() -> str:
    """Get base lakehouse path from config."""
    return Config.LAKEHOUSE_PATH


def get_bronze_path(dataset: str = "movielens", version: str = "ml-25m") -> str:
    """
    Get Bronze layer path.
    
    Args:
        dataset: Dataset name (default: movielens)
        version: Dataset version (default: ml-25m)
    
    Returns:
        Full path to Bronze dataset directory
    """
    base = get_lakehouse_base()
    return os.path.join(base, "bronze", dataset, version)


def get_silver_path(table_name: str) -> str:
    """
    Get Silver layer table path.
    
    Args:
        table_name: Table name (e.g., 'ratings', 'movies', 'tags')
    
    Returns:
        Full path to Silver table
    """
    base = get_lakehouse_base()
    return os.path.join(base, "silver", table_name)


def get_gold_path(table_name: str) -> str:
    """
    Get Gold layer table path.
    
    Args:
        table_name: Table name (e.g., 'recommendations_als', 'trending_now')
    
    Returns:
        Full path to Gold table
    """
    base = get_lakehouse_base()
    return os.path.join(base, "gold", table_name)


def get_reports_path(layer: str = "silver") -> str:
    """
    Get reports directory path.
    
    Args:
        layer: Layer name (silver or gold)
    
    Returns:
        Full path to reports directory
    """
    base = get_lakehouse_base()
    return os.path.join(base, layer, "_reports")


def get_models_path(model_name: str, version: Optional[str] = None) -> str:
    """
    Get model storage path.
    
    Args:
        model_name: Model name (e.g., 'als')
        version: Model version (optional)
    
    Returns:
        Full path to model directory
    """
    base = get_lakehouse_base()
    if version:
        return os.path.join(base, "gold", "models", model_name, version)
    return os.path.join(base, "gold", "models", model_name)


def get_metrics_path() -> str:
    """Get metrics storage path."""
    base = get_lakehouse_base()
    return os.path.join(base, "gold", "metrics")


def ensure_directory_exists(path: str) -> None:
    """Ensure directory exists, create if not."""
    Path(path).mkdir(parents=True, exist_ok=True)

