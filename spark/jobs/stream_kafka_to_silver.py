#!/usr/bin/env python3
"""
Streaming Job: Kafka → Silver
Reads events from Kafka topics, validates and cleans, writes to Silver layer.
Uses Spark Structured Streaming with checkpointing and dead-letter handling.
"""

import sys
import os
import json
from datetime import datetime
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
    col, from_json, to_timestamp, date_format, current_timestamp, 
    when, lit, regexp_replace, split, explode
)

from reco_platform.config import Config
from reco_platform.paths import get_silver_path, ensure_directory_exists


def create_spark_session() -> SparkSession:
    """Create Spark session with streaming support."""
    builder = SparkSession.builder \
        .appName("Stream_Kafka_to_Silver") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.streaming.checkpointLocation", 
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_kafka_to_silver"))
    
    if Config.STORAGE_FORMAT == "delta":
        builder = builder \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    
    return builder.getOrCreate()


def define_view_event_schema() -> StructType:
    """Define schema for view events."""
    return StructType([
        StructField("event_id", StringType(), False),
        StructField("event_type", StringType(), False),
        StructField("event_ts", StringType(), False),  # ISO-8601 string
        StructField("user_id", IntegerType(), False),
        StructField("movie_id", IntegerType(), False),
        StructField("session_id", StringType(), True),
        StructField("device_type", StringType(), True),
        StructField("page_url", StringType(), True),
    ])


def define_click_event_schema() -> StructType:
    """Define schema for click events."""
    return StructType([
        StructField("event_id", StringType(), False),
        StructField("event_type", StringType(), False),
        StructField("event_ts", StringType(), False),
        StructField("user_id", IntegerType(), False),
        StructField("movie_id", IntegerType(), False),
        StructField("click_type", StringType(), True),
        StructField("session_id", StringType(), True),
        StructField("referrer", StringType(), True),
    ])


def define_rating_event_schema() -> StructType:
    """Define schema for rating events."""
    return StructType([
        StructField("event_id", StringType(), False),
        StructField("event_type", StringType(), False),
        StructField("event_ts", StringType(), False),
        StructField("user_id", IntegerType(), False),
        StructField("movie_id", IntegerType(), False),
        StructField("rating", FloatType(), False),
        StructField("review_text", StringType(), True),
    ])


def parse_and_validate_stream(df, schema: StructType, topic_name: str):
    """Parse JSON and validate events, separate valid and invalid records."""
    # Parse JSON with schema
    parsed_df = df.select(
        col("key").cast("string"),
        col("value").cast("string"),
        col("timestamp"),
        from_json(col("value").cast("string"), schema).alias("data")
    )
    
    # Extract valid records
    valid_df = parsed_df.filter(col("data").isNotNull()).select(
        col("data.*"),
        col("timestamp").alias("kafka_ts")
    )
    
    # Extract invalid records (dead letter)
    invalid_df = parsed_df.filter(col("data").isNull()).select(
        col("value").alias("raw_payload"),
        lit(topic_name).alias("topic"),
        lit("schema_validation_failed").alias("error_reason"),
        current_timestamp().alias("error_ts")
    )
    
    return valid_df, invalid_df


def process_view_events(spark: SparkSession, kafka_bootstrap_servers: str):
    """Process view events from Kafka to Silver."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STREAM] Processing events_views")
    
    # Read from Kafka
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", "events_views") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    schema = define_view_event_schema()
    valid_df, invalid_df = parse_and_validate_stream(kafka_df, schema, "events_views")
    
    # Transform valid records
    silver_df = valid_df \
        .withColumn("event_ts", to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")) \
        .withColumn("event_date", date_format(col("event_ts"), "yyyy-MM-dd").cast(DateType())) \
        .select(
            col("event_id"),
            col("event_ts"),
            col("user_id"),
            col("movie_id"),
            col("session_id"),
            col("device_type"),
            col("event_date")
        ) \
        .filter(
            col("event_id").isNotNull() &
            col("user_id").isNotNull() &
            col("movie_id").isNotNull() &
            col("event_ts").isNotNull()
        )
    
    # Write valid records to Silver
    silver_path = get_silver_path("events_views")
    ensure_directory_exists(os.path.dirname(silver_path))
    
    query_valid = silver_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("append") \
        .trigger(processingTime='5 seconds') \
        .option("checkpointLocation", 
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_kafka_to_silver", "events_views")) \
        .partitionBy("event_date") \
        .start(silver_path)
    
    # Write invalid records to dead letter
    deadletter_path = os.path.join(Config.LAKEHOUSE_PATH, "silver", "_deadletter", "events_views")
    ensure_directory_exists(deadletter_path)
    
    query_invalid = invalid_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("append") \
        .trigger(processingTime='5 seconds') \
        .option("checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_kafka_to_silver", "events_views_dlq")) \
        .start(deadletter_path)
    
    return query_valid, query_invalid


def process_click_events(spark: SparkSession, kafka_bootstrap_servers: str):
    """Process click events from Kafka to Silver."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STREAM] Processing events_clicks")
    
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", "events_clicks") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    schema = define_click_event_schema()
    valid_df, invalid_df = parse_and_validate_stream(kafka_df, schema, "events_clicks")
    
    silver_df = valid_df \
        .withColumn("event_ts", to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")) \
        .withColumn("event_date", date_format(col("event_ts"), "yyyy-MM-dd").cast(DateType())) \
        .select(
            col("event_id"),
            col("event_ts"),
            col("user_id"),
            col("movie_id"),
            col("click_type"),
            col("session_id"),
            col("referrer"),
            col("event_date")
        ) \
        .filter(
            col("event_id").isNotNull() &
            col("user_id").isNotNull() &
            col("movie_id").isNotNull() &
            col("event_ts").isNotNull()
        )
    
    silver_path = get_silver_path("events_clicks")
    ensure_directory_exists(os.path.dirname(silver_path))
    
    query_valid = silver_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("append") \
        .trigger(processingTime='5 seconds') \
        .option("checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_kafka_to_silver", "events_clicks")) \
        .partitionBy("event_date") \
        .start(silver_path)
    
    deadletter_path = os.path.join(Config.LAKEHOUSE_PATH, "silver", "_deadletter", "events_clicks")
    ensure_directory_exists(deadletter_path)
    
    query_invalid = invalid_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("append") \
        .trigger(processingTime='5 seconds') \
        .option("checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_kafka_to_silver", "events_clicks_dlq")) \
        .start(deadletter_path)
    
    return query_valid, query_invalid


def process_rating_events(spark: SparkSession, kafka_bootstrap_servers: str):
    """Process rating events from Kafka to Silver."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STREAM] Processing events_ratings")
    
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", "events_ratings") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    schema = define_rating_event_schema()
    valid_df, invalid_df = parse_and_validate_stream(kafka_df, schema, "events_ratings")
    
    silver_df = valid_df \
        .withColumn("event_ts", to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")) \
        .withColumn("event_date", date_format(col("event_ts"), "yyyy-MM-dd").cast(DateType())) \
        .select(
            col("event_id"),
            col("event_ts"),
            col("user_id"),
            col("movie_id"),
            col("rating"),
            col("review_text"),
            col("event_date")
        ) \
        .filter(
            col("event_id").isNotNull() &
            col("user_id").isNotNull() &
            col("movie_id").isNotNull() &
            col("event_ts").isNotNull() &
            col("rating").isNotNull() &
            (col("rating") >= Config.MIN_RATING) &
            (col("rating") <= Config.MAX_RATING)
        )
    
    silver_path = get_silver_path("events_ratings")
    ensure_directory_exists(os.path.dirname(silver_path))
    
    query_valid = silver_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("append") \
        .trigger(processingTime='5 seconds') \
        .option("checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_kafka_to_silver", "events_ratings")) \
        .partitionBy("event_date") \
        .start(silver_path)
    
    deadletter_path = os.path.join(Config.LAKEHOUSE_PATH, "silver", "_deadletter", "events_ratings")
    ensure_directory_exists(deadletter_path)
    
    query_invalid = invalid_df.writeStream \
        .format(Config.STORAGE_FORMAT) \
        .outputMode("append") \
        .trigger(processingTime='5 seconds') \
        .option("checkpointLocation",
                os.path.join(Config.LAKEHOUSE_PATH, "_checkpoints", "stream_kafka_to_silver", "events_ratings_dlq")) \
        .start(deadletter_path)
    
    return query_valid, query_invalid


def main():
    """Main streaming function."""
    job_start_time = datetime.now()
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Streaming Job: Kafka → Silver")
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Lakehouse path: {Config.LAKEHOUSE_PATH}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Storage format: {Config.STORAGE_FORMAT}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Kafka bootstrap servers: {Config.KAFKA_BOOTSTRAP_SERVERS}")
    print()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INIT] Creating SparkSession...")
    spark = create_spark_session()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INIT] SparkSession created")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Spark version: {spark.version}")
    print()
    
    queries = []
    
    try:
        # Start all streaming queries
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Starting streaming queries...")
        
        # Process each topic
        q1_valid, q1_invalid = process_view_events(spark, Config.KAFKA_BOOTSTRAP_SERVERS)
        queries.extend([q1_valid, q1_invalid])
        
        q2_valid, q2_invalid = process_click_events(spark, Config.KAFKA_BOOTSTRAP_SERVERS)
        queries.extend([q2_valid, q2_invalid])
        
        q3_valid, q3_invalid = process_rating_events(spark, Config.KAFKA_BOOTSTRAP_SERVERS)
        queries.extend([q3_valid, q3_invalid])
        
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

