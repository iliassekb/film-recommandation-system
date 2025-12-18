#!/usr/bin/env python3
"""
ETL Job: Bronze → Silver
Reads MovieLens CSV files from Bronze, cleans and validates, writes to Silver layer.
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add src to path for imports
# Try multiple paths for flexibility
src_paths = [
    os.path.join(os.path.dirname(__file__), '../../src'),
    '/opt/spark/src',
    os.path.join(os.path.dirname(__file__), '..', '..', 'src')
]
for path in src_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)
        break

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, IntegerType, FloatType, StringType, TimestampType
)
from pyspark.sql.functions import col, from_unixtime, year, month, lit, current_timestamp

from reco_platform.config import Config
from reco_platform.paths import (
    get_bronze_path, get_silver_path, get_reports_path, ensure_directory_exists
)
from reco_platform.io import read_csv_with_schema, write_table
from reco_platform.quality import QualityReport, validate_ratings, validate_movies, validate_tags


def create_spark_session() -> SparkSession:
    """Create Spark session with Delta Lake support if needed."""
    builder = SparkSession.builder \
        .appName("ETL_Bronze_to_Silver") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    if Config.STORAGE_FORMAT == "delta":
        builder = builder \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    
    return builder.getOrCreate()


def define_ratings_schema() -> StructType:
    """Define schema for ratings CSV."""
    return StructType([
        StructField("user_id", IntegerType(), False),
        StructField("movie_id", IntegerType(), False),
        StructField("rating", FloatType(), False),
        StructField("timestamp", IntegerType(), False)  # Unix timestamp in seconds
    ])


def define_movies_schema() -> StructType:
    """Define schema for movies CSV."""
    return StructType([
        StructField("movie_id", IntegerType(), False),
        StructField("title", StringType(), False),
        StructField("genres", StringType(), False)
    ])


def define_tags_schema() -> StructType:
    """Define schema for tags CSV."""
    return StructType([
        StructField("user_id", IntegerType(), False),
        StructField("movie_id", IntegerType(), False),
        StructField("tag", StringType(), False),
        StructField("timestamp", IntegerType(), False)  # Unix timestamp in seconds
    ])


def count_csv_lines_fast(file_path: str) -> int:
    """
    Quickly count lines in a CSV file using Python (excluding header).
    Much faster than Spark count() for initial estimation.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Number of data rows (excluding header)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Skip header
            next(f, None)
            # Count remaining lines
            return sum(1 for _ in f)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Could not count lines in {file_path}: {e}")
        return -1


def process_ratings(spark: SparkSession, bronze_path: str) -> tuple:
    """Process ratings CSV from Bronze to Silver."""
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STEP 1/3] Processing ratings from {bronze_path}")
    
    ratings_path = os.path.join(bronze_path, "ratings.csv")
    if not os.path.exists(ratings_path):
        raise FileNotFoundError(f"Ratings file not found: {ratings_path}")
    
    # Count lines before processing (fast Python method)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Counting lines in CSV file (fast method)...")
    count_start = time.time()
    total_lines = count_csv_lines_fast(ratings_path)
    count_elapsed = time.time() - count_start
    if total_lines > 0:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] ✓ Total lines in file: {total_lines:,} (counted in {count_elapsed:.2f}s)")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Could not count lines, will use Spark count()")
    
    file_size_mb = os.path.getsize(ratings_path) / (1024 * 1024)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] File size: {file_size_mb:.1f} MB")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [0%] Creating DataFrame schema...")
    # Read with explicit schema (lazy operation - no data read yet)
    schema = define_ratings_schema()
    read_start = time.time()
    df = read_csv_with_schema(spark, ratings_path, schema)
    read_elapsed = time.time() - read_start
    print(df.head(5))
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [5%] DataFrame schema created in {read_elapsed:.2f}s")
    
    # Calculate estimated time based on file size
    estimated_seconds = max(30, (file_size_mb / 100) * 60)
    estimated_minutes = estimated_seconds / 60
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [5%] Reading and parsing CSV file...")
    count_start = time.time()
    initial_count = df.count()
    
    count_elapsed = time.time() - count_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [25%] ✓ Initial count: {initial_count:,} rows (took {count_elapsed:.2f}s = {count_elapsed/60:.2f} min)")
    if total_lines > 0 and abs(initial_count - total_lines) > 1000:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Note: Line count difference: file has {total_lines:,} lines, Spark counted {initial_count:,} (header excluded)")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [25%] Applying transformations...")
    transform_start = time.time()
    # Transformations: Convert Unix timestamp (seconds) to TimestampType
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [30%] Converting timestamps...")
    df = df.withColumn(
        "rating_ts",
        from_unixtime(col("timestamp")).cast(TimestampType())
    ).drop("timestamp")
    
    # Cleaning rules
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [40%] Filtering null values...")
    df = df.filter(col("user_id").isNotNull() & col("movie_id").isNotNull())
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [50%] Filtering rating range...")
    df = df.filter(
        (col("rating") >= Config.MIN_RATING) & 
        (col("rating") <= Config.MAX_RATING)
    )
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [60%] Removing duplicates...")
    df = df.dropDuplicates(["user_id", "movie_id", "rating_ts"])
    transform_elapsed = time.time() - transform_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [70%] Transformations completed in {transform_elapsed:.2f}s")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [70%] Counting final rows after cleaning...")
    count_start = time.time()
    final_count = df.count()
    count_elapsed = time.time() - count_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [85%] ✓ Final count: {final_count:,} rows (took {count_elapsed:.2f}s)")
    dropped_count = initial_count - final_count
    dropped_pct = (dropped_count / initial_count * 100) if initial_count > 0 else 0
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Dropped: {dropped_count:,} rows ({dropped_pct:.2f}%)")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [85%] Adding partition columns...")
    df = df.withColumn("year", year(col("rating_ts")))
    df = df.withColumn("month", month(col("rating_ts")))
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [90%] Partition columns added")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [90%] Running quality validation...")
    report = QualityReport("ratings")
    validate_ratings(df, report)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [100%] Quality validation completed")
    
    elapsed = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Ratings processing completed in {elapsed:.2f}s ({elapsed/60:.2f} minutes)")
    print()
    
    # Add partition columns (year and month)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Adding partition columns (year, month)...")
    df = df.withColumn("year", year(col("rating_ts")))
    df = df.withColumn("month", month(col("rating_ts")))
    
    # Validate
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Running quality validation...")
    report = QualityReport("ratings")
    validate_ratings(df, report)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Quality validation completed")
    
    elapsed = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Ratings processing completed in {elapsed:.2f}s")
    print()
    
    return df, report


def process_movies(spark: SparkSession, bronze_path: str) -> tuple:
    """Process movies CSV from Bronze to Silver."""
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STEP 2/3] Processing movies from {bronze_path}")
    
    movies_path = os.path.join(bronze_path, "movies.csv")
    if not os.path.exists(movies_path):
        raise FileNotFoundError(f"Movies file not found: {movies_path}")
    
    # Count lines before processing (fast Python method)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Counting lines in CSV file (fast method)...")
    count_start = time.time()
    total_lines = count_csv_lines_fast(movies_path)
    count_elapsed = time.time() - count_start
    if total_lines > 0:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] ✓ Total lines in file: {total_lines:,} (counted in {count_elapsed:.2f}s)")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Could not count lines, will use Spark count()")
    
    file_size_mb = os.path.getsize(movies_path) / (1024 * 1024)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] File size: {file_size_mb:.1f} MB")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [0%] Creating DataFrame schema...")
    # Read with explicit schema (lazy operation)
    schema = define_movies_schema()
    read_start = time.time()
    df = read_csv_with_schema(spark, movies_path, schema)
    read_elapsed = time.time() - read_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [10%] DataFrame schema created in {read_elapsed:.2f}s")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [10%] Reading and parsing CSV file...")
    count_start = time.time()
    initial_count = df.count()
    count_elapsed = time.time() - count_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [30%] ✓ Initial count: {initial_count:,} rows (took {count_elapsed:.2f}s)")
    if total_lines > 0 and abs(initial_count - total_lines) > 100:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Note: Line count difference: file has {total_lines:,} lines, Spark counted {initial_count:,} (header excluded)")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [30%] Applying transformations...")
    transform_start = time.time()
    
    # Extract release year from title (format: "Title (YYYY)")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [40%] Extracting release year from title...")
    from pyspark.sql.functions import regexp_extract
    df = df.withColumn(
        "release_year",
        regexp_extract(col("title"), r"\((\d{4})\)", 1).cast(IntegerType())
    )
    
    # Split genres string into array
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [50%] Splitting genres into array...")
    from pyspark.sql.functions import split
    df = df.withColumn("genres_array", split(col("genres"), "\\|"))
    
    # Rename genres to genres_string for clarity
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [60%] Renaming genre columns...")
    df = df.withColumnRenamed("genres", "genres_string")
    df = df.withColumnRenamed("genres_array", "genres")
    
    # Drop nulls in required fields
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [70%] Filtering null values...")
    df = df.filter(col("movie_id").isNotNull() & col("title").isNotNull())
    
    # Deduplicate by movie_id (keep first)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [80%] Removing duplicates...")
    df = df.dropDuplicates(["movie_id"])
    transform_elapsed = time.time() - transform_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [85%] Transformations completed in {transform_elapsed:.2f}s")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [85%] Counting final rows...")
    count_start = time.time()
    final_count = df.count()
    count_elapsed = time.time() - count_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [90%] ✓ Final count: {final_count:,} rows (took {count_elapsed:.2f}s)")
    if initial_count != final_count:
        dropped_count = initial_count - final_count
        dropped_pct = (dropped_count / initial_count * 100) if initial_count > 0 else 0
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Dropped: {dropped_count:,} rows ({dropped_pct:.2f}%)")
    print()
    
    # Validate
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [90%] Running quality validation...")
    report = QualityReport("movies")
    validate_movies(df, report)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [100%] Quality validation completed")
    
    elapsed = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Movies processing completed in {elapsed:.2f}s ({elapsed/60:.2f} minutes)")
    print()
    
    return df, report


def process_tags(spark: SparkSession, bronze_path: str) -> tuple:
    """Process tags CSV from Bronze to Silver."""
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STEP 3/3] Processing tags from {bronze_path}")
    
    tags_path = os.path.join(bronze_path, "tags.csv")
    if not os.path.exists(tags_path):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Tags file not found: {tags_path}, skipping")
        return None, None
    
    # Count lines before processing (fast Python method)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Counting lines in CSV file (fast method)...")
    count_start = time.time()
    total_lines = count_csv_lines_fast(tags_path)
    count_elapsed = time.time() - count_start
    if total_lines > 0:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] ✓ Total lines in file: {total_lines:,} (counted in {count_elapsed:.2f}s)")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Could not count lines, will use Spark count()")
    
    file_size_mb = os.path.getsize(tags_path) / (1024 * 1024)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] File size: {file_size_mb:.1f} MB")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [0%] Creating DataFrame schema...")
    # Read with explicit schema (lazy operation)
    schema = define_tags_schema()
    read_start = time.time()
    df = read_csv_with_schema(spark, tags_path, schema)
    read_elapsed = time.time() - read_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [10%] DataFrame schema created in {read_elapsed:.2f}s")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [10%] Reading and parsing CSV file...")
    count_start = time.time()
    initial_count = df.count()
    count_elapsed = time.time() - count_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [30%] ✓ Initial count: {initial_count:,} rows (took {count_elapsed:.2f}s)")
    if total_lines > 0 and abs(initial_count - total_lines) > 100:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Note: Line count difference: file has {total_lines:,} lines, Spark counted {initial_count:,} (header excluded)")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [30%] Applying transformations...")
    transform_start = time.time()
    
    # Transformations: Convert Unix timestamp (seconds) to TimestampType
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [40%] Converting timestamps...")
    df = df.withColumn(
        "tag_ts",
        from_unixtime(col("timestamp")).cast(TimestampType())
    ).drop("timestamp")
    
    # Cleaning
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [50%] Filtering null values...")
    df = df.filter(
        col("user_id").isNotNull() & 
        col("movie_id").isNotNull() & 
        col("tag").isNotNull()
    )
    
    # Add partition columns
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [60%] Adding partition columns...")
    df = df.withColumn("year", year(col("tag_ts")))
    df = df.withColumn("month", month(col("tag_ts")))
    transform_elapsed = time.time() - transform_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [70%] Transformations completed in {transform_elapsed:.2f}s")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [70%] Counting final rows...")
    count_start = time.time()
    final_count = df.count()
    count_elapsed = time.time() - count_start
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [85%] ✓ Final count: {final_count:,} rows (took {count_elapsed:.2f}s)")
    if initial_count != final_count:
        dropped_count = initial_count - final_count
        dropped_pct = (dropped_count / initial_count * 100) if initial_count > 0 else 0
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Dropped: {dropped_count:,} rows ({dropped_pct:.2f}%)")
    print()
    
    # Validate
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [85%] Running quality validation...")
    report = QualityReport("tags")
    validate_tags(df, report)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] [100%] Quality validation completed")
    
    elapsed = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Tags processing completed in {elapsed:.2f}s ({elapsed/60:.2f} minutes)")
    print()
    
    return df, report


def write_silver_tables(
    spark: SparkSession,
    ratings_df,
    movies_df,
    tags_df,
    report_paths: dict
) -> dict:
    """Write cleaned DataFrames to Silver layer."""
    results = {}
    write_start_total = time.time()
    
    # Write ratings
    if ratings_df is not None:
        silver_ratings_path = get_silver_path("ratings")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WRITE] Writing ratings to {silver_ratings_path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Format: {Config.STORAGE_FORMAT}, Partitions: year, month")
        # Cache count before writing to avoid recomputing
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Getting row count before write...")
        count_start = time.time()
        row_count = ratings_df.count()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Rows to write: {row_count:,} (took {time.time() - count_start:.2f}s)")
        write_start = time.time()
        write_table(
            ratings_df,
            silver_ratings_path,
            mode="overwrite",
            partition_by=["year", "month"]
        )
        write_elapsed = time.time() - write_start
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Write completed in {write_elapsed:.2f}s")
        results["ratings"] = {
            "path": silver_ratings_path,
            "row_count": row_count,
            "report_path": report_paths.get("ratings")
        }
        print()
    
    # Write movies
    if movies_df is not None:
        silver_movies_path = get_silver_path("movies")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WRITE] Writing movies to {silver_movies_path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Format: {Config.STORAGE_FORMAT}, No partitions")
        # Cache count before writing to avoid recomputing
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Getting row count before write...")
        count_start = time.time()
        row_count = movies_df.count()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Rows to write: {row_count:,} (took {time.time() - count_start:.2f}s)")
        write_start = time.time()
        write_table(movies_df, silver_movies_path, mode="overwrite")
        write_elapsed = time.time() - write_start
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Write completed in {write_elapsed:.2f}s")
        results["movies"] = {
            "path": silver_movies_path,
            "row_count": row_count,
            "report_path": report_paths.get("movies")
        }
        print()
    
    # Write tags
    if tags_df is not None:
        silver_tags_path = get_silver_path("tags")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WRITE] Writing tags to {silver_tags_path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Format: {Config.STORAGE_FORMAT}, Partitions: year, month")
        # Cache count before writing to avoid recomputing
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Getting row count before write...")
        count_start = time.time()
        row_count = tags_df.count()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Rows to write: {row_count:,} (took {time.time() - count_start:.2f}s)")
        write_start = time.time()
        write_table(
            tags_df,
            silver_tags_path,
            mode="overwrite",
            partition_by=["year", "month"]
        )
        write_elapsed = time.time() - write_start
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Write completed in {write_elapsed:.2f}s")
        results["tags"] = {
            "path": silver_tags_path,
            "row_count": row_count,
            "report_path": report_paths.get("tags")
        }
        print()
    
    total_elapsed = time.time() - write_start_total
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] All Silver tables written in {total_elapsed:.2f}s")
    print()
    
    return results


def generate_etl_report(results: dict, reports: dict) -> str:
    """Generate ETL execution report."""
    report_dir = get_reports_path("silver")
    ensure_directory_exists(report_dir)
    
    report_path = os.path.join(
        report_dir,
        f"etl_bronze_to_silver_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    report_data = {
        "etl_job": "bronze_to_silver",
        "execution_ts": datetime.utcnow().isoformat() + "Z",
        "storage_format": Config.STORAGE_FORMAT,
        "tables_processed": list(results.keys()),
        "results": results,
        "quality_reports": {
            table: reports[table].to_dict() if reports.get(table) else None
            for table in results.keys()
        }
    }
    
    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"[INFO] ETL report saved to: {report_path}")
    return report_path


def test_file_access(bronze_path: str) -> bool:
    """
    Test file access by reading a small file (genome-tags.csv) with Python standard library.
    This verifies file system access without Spark overhead.
    
    Returns:
        True if test successful, False otherwise
    """
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TEST] Testing file access with genome-tags.csv (smallest file)")
    print("=" * 80)
    
    genome_tags_path = os.path.join(bronze_path, "genome-tags.csv")
    
    if not os.path.exists(genome_tags_path):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] genome-tags.csv not found at {genome_tags_path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] This file is optional - skipping test")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Will proceed with main ETL processing")
        print()
        return True  # Not a failure, just optional file missing
    
    try:
        file_size_mb = os.path.getsize(genome_tags_path) / (1024 * 1024)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] File found: {genome_tags_path}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] File size: {file_size_mb:.2f} MB")
        
        # Read file directly with Python (fast, no Spark overhead)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Reading first 5 lines with Python (fast test)...")
        read_start = time.time()
        
        with open(genome_tags_path, 'r', encoding='utf-8') as f:
            # Read header
            header = f.readline().strip()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Header: {header}")
            
            # Read first 5 data rows
            sample_rows = []
            for i in range(5):
                line = f.readline().strip()
                if not line:
                    break
                sample_rows.append(line)
        
        read_elapsed = time.time() - read_start
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] ✓ Successfully read {len(sample_rows)} rows in {read_elapsed:.3f}s")
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Sample data (first {len(sample_rows)} rows):")
        for i, row in enumerate(sample_rows, 1):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO]   Row {i}: {row}")
        
        # Quick line count (without loading full file)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Counting total lines (excluding header)...")
        count_start = time.time()
        with open(genome_tags_path, 'r', encoding='utf-8') as f:
            # Skip header
            next(f)
            # Count remaining lines
            total_count = sum(1 for _ in f)
        count_elapsed = time.time() - count_start
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] ✓ Total rows: {total_count:,} (count took {count_elapsed:.3f}s)")
        
        print()
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] File access test passed! Files are accessible.")
        print("=" * 80)
        print()
        return True
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] File access test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Continuing with main ETL anyway...")
        print("=" * 80)
        print()
        return False  # Test failed but continue anyway


def main():
    """Main ETL function."""
    job_start_time = time.time()
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ETL Job: Bronze → Silver")
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Lakehouse path: {Config.LAKEHOUSE_PATH}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Storage format: {Config.STORAGE_FORMAT}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Spark master: {Config.SPARK_MASTER}")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INIT] Creating SparkSession...")
    spark_start = time.time()
    spark = create_spark_session()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INIT] SparkSession created in {time.time() - spark_start:.2f}s")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Spark version: {spark.version}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Spark app name: {spark.sparkContext.appName}")
    print()
    
    try:
        
        # Get paths
        bronze_path = get_bronze_path()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Bronze path: {bronze_path}")
        print()
        
        # Test file access with smallest file first (using Python, not Spark, for speed)
        test_file_access(bronze_path)
        
        # Process each table
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PHASE 1] Processing Bronze tables")
        print("=" * 80)
        ratings_df, ratings_report = process_ratings(spark, bronze_path)
        movies_df, movies_report = process_movies(spark, bronze_path)
        tags_df, tags_report = process_tags(spark, bronze_path)
        
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PHASE 2] Saving quality reports")
        print("=" * 80)
        report_start = time.time()
        report_paths = {}
        if ratings_report:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Saving ratings quality report...")
            report_paths["ratings"] = ratings_report.save(spark, "silver")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Saved to: {report_paths['ratings']}")
        if movies_report:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Saving movies quality report...")
            report_paths["movies"] = movies_report.save(spark, "silver")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Saved to: {report_paths['movies']}")
        if tags_report:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Saving tags quality report...")
            report_paths["tags"] = tags_report.save(spark, "silver")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Saved to: {report_paths['tags']}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] Quality reports saved in {time.time() - report_start:.2f}s")
        print()
        
        # Write Silver tables
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PHASE 3] Writing Silver tables")
        print("=" * 80)
        results = write_silver_tables(
            spark,
            ratings_df,
            movies_df,
            tags_df,
            report_paths
        )
        
        # Generate ETL report
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [PHASE 4] Generating ETL report")
        print("=" * 80)
        report_start = time.time()
        etl_report_path = generate_etl_report(results, {
            "ratings": ratings_report,
            "movies": movies_report,
            "tags": tags_report
        })
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] ETL report generated in {time.time() - report_start:.2f}s")
        print()
        
        job_elapsed = time.time() - job_start_time
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] ETL Bronze → Silver completed successfully!")
        print("=" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUMMARY] Total execution time: {job_elapsed:.2f}s ({job_elapsed/60:.2f} minutes)")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUMMARY] Tables written: {len(results)}")
        for table, info in results.items():
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUMMARY]   - {table}: {info['row_count']:,} rows -> {info['path']}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUMMARY] ETL Report: {etl_report_path}")
        print("=" * 80)
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] ETL job failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CLEANUP] Stopping SparkSession...")
        spark.stop()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CLEANUP] SparkSession stopped")


if __name__ == "__main__":
    main()

