#!/usr/bin/env python3
"""
Streaming Job: Silver Events → Gold Trending
Consumes Silver event tables, computes windowed aggregates for trending movies.
Uses Spark Structured Streaming with watermarking and window functions.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
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
    StructType, StructField, StringType, IntegerType, FloatType, TimestampType, DateType
)
from pyspark.sql.functions import (
    col, window, count, sum as spark_sum, max as spark_max,
    current_timestamp, lit, when, coalesce
)

from reco_platform.config import Config
from reco_platform.paths import get_silver_path, get_gold_path, ensure_directory_exists


def create_spark_session() -> SparkSession:
    """Create Spark session with streaming support."""
    builder = SparkSession.builder \
        .appName("Stream_Trending_to_Gold") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.streaming.checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_trending_to_gold"))
    
    if Config.STORAGE_FORMAT == "delta":
        builder = builder \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    
    return builder.getOrCreate()


def compute_trending_1h(spark: SparkSession):
    """Compute 1-hour rolling window trending scores."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STREAM] Computing trending_now_1h")
    
    # Read views
    views_path = get_silver_path("events_views")
    views_df = spark.readStream.format(Config.STORAGE_FORMAT).load(views_path)
    
    # Read clicks
    clicks_path = get_silver_path("events_clicks")
    clicks_df = spark.readStream.format(Config.STORAGE_FORMAT).load(clicks_path)
    
    # Aggregate views per movie in 1h windows
    views_agg = views_df \
        .withWatermark("event_ts", "2 hours") \
        .groupBy(
            window(col("event_ts"), "1 hour"),
            col("movie_id")
        ) \
        .agg(
            count("*").alias("views")
        ) \
        .select(
            col("window.end").alias("window_end"),
            col("movie_id"),
            col("views")
        )
    
    # Aggregate clicks per movie in 1h windows
    clicks_agg = clicks_df \
        .withWatermark("event_ts", "2 hours") \
        .groupBy(
            window(col("event_ts"), "1 hour"),
            col("movie_id")
        ) \
        .agg(
            count("*").alias("clicks")
        ) \
        .select(
            col("window.end").alias("window_end"),
            col("movie_id"),
            col("clicks")
        )
    
    # Join and compute trend score
    trending_df = views_agg \
        .join(clicks_agg, ["window_end", "movie_id"], "outer") \
        .select(
            col("window_end").alias("window_ts"),
            col("movie_id"),
            coalesce(col("views"), lit(0)).alias("views"),
            coalesce(col("clicks"), lit(0)).alias("clicks"),
            (coalesce(col("views"), lit(0)) * 1.0 + coalesce(col("clicks"), lit(0)) * 2.0).alias("trend_score")
        ) \
        .orderBy(col("trend_score").desc())
    
    # Write to Gold
    gold_path = get_gold_path("trending_now_1h")
    ensure_directory_exists(os.path.dirname(gold_path))
    
    query = trending_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("complete") \
        .option("checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_trending_to_gold", "trending_1h")) \
        .trigger(processingTime="5 seconds") \
        .start(gold_path)
    
    return query


def compute_trending_24h(spark: SparkSession):
    """Compute 24-hour rolling window trending scores."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STREAM] Computing trending_now_24h")
    
    # Read views
    views_path = get_silver_path("events_views")
    views_df = spark.readStream.format(Config.STORAGE_FORMAT).load(views_path)
    
    # Read clicks
    clicks_path = get_silver_path("events_clicks")
    clicks_df = spark.readStream.format(Config.STORAGE_FORMAT).load(clicks_path)
    
    # Aggregate views per movie in 24h windows
    views_agg = views_df \
        .withWatermark("event_ts", "26 hours") \
        .groupBy(
            window(col("event_ts"), "24 hours", "1 hour"),  # 24h window, slide 1h
            col("movie_id")
        ) \
        .agg(
            count("*").alias("views")
        ) \
        .select(
            col("window.end").alias("window_end"),
            col("movie_id"),
            col("views")
        )
    
    # Aggregate clicks per movie in 24h windows
    clicks_agg = clicks_df \
        .withWatermark("event_ts", "26 hours") \
        .groupBy(
            window(col("event_ts"), "24 hours", "1 hour"),
            col("movie_id")
        ) \
        .agg(
            count("*").alias("clicks")
        ) \
        .select(
            col("window.end").alias("window_end"),
            col("movie_id"),
            col("clicks")
        )
    
    # Join and compute trend score
    trending_df = views_agg \
        .join(clicks_agg, ["window_end", "movie_id"], "outer") \
        .select(
            col("window_end").alias("window_ts"),
            col("movie_id"),
            coalesce(col("views"), lit(0)).alias("views"),
            coalesce(col("clicks"), lit(0)).alias("clicks"),
            (coalesce(col("views"), lit(0)) * 1.0 + coalesce(col("clicks"), lit(0)) * 2.0).alias("trend_score")
        ) \
        .orderBy(col("trend_score").desc())
    
    # Write to Gold
    gold_path = get_gold_path("trending_now_24h")
    ensure_directory_exists(os.path.dirname(gold_path))
    
    query = trending_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("complete") \
        .option("checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_trending_to_gold", "trending_24h")) \
        .trigger(processingTime="5 seconds") \
        .start(gold_path)
    
    return query


def main():
    """Main streaming function."""
    job_start_time = datetime.now()
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Streaming Job: Silver → Gold Trending")
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Lakehouse path: {Config.LAKEHOUSE_PATH}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Storage format: {Config.STORAGE_FORMAT}")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INIT] Creating SparkSession...")
    spark = create_spark_session()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INIT] SparkSession created")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Spark version: {spark.version}")
    print()
    
    queries = []
    
    try:
        # Start streaming queries
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Starting streaming queries...")
        
        q1 = compute_trending_1h(spark)
        queries.append(q1)
        
        q2 = compute_trending_24h(spark)
        queries.append(q2)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] All streaming queries started ({len(queries)} total)")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Waiting for streaming queries to complete...")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Press Ctrl+C to stop")
        print()
        
        # Wait for all queries (this blocks until stopped)
        for query in queries:
            query.awaitTermination()
            
    except KeyboardInterrupt:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Stopping streaming queries...")
        for query in queries:
            try:
                query.stop()
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Error stopping query: {e}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] All queries stopped")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Streaming job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CLEANUP] Stopping SparkSession...")
        spark.stop()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CLEANUP] SparkSession stopped")


if __name__ == "__main__":
    main()

