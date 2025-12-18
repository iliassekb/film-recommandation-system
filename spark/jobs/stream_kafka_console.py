#!/usr/bin/env python3
"""
Streaming Job: Kafka → Console Display
Reads events from the 3 Kafka topics (events_views, events_clicks, events_ratings)
and displays them in the console using Spark Structured Streaming.
"""

import sys
import os
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
    StructType, StructField, StringType, IntegerType, FloatType, TimestampType
)
from pyspark.sql.functions import (
    col, from_json, to_timestamp, current_timestamp, lit
)

from reco_platform.config import Config


def create_spark_session() -> SparkSession:
    """Create Spark session with streaming support."""
    builder = SparkSession.builder \
        .appName("Stream_Kafka_Console") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints/stream_kafka_console")
    
    if Config.STORAGE_FORMAT == "delta":
        builder = builder \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


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


def parse_kafka_stream(df, schema: StructType, topic_name: str):
    """Parse JSON from Kafka stream."""
    parsed_df = df.select(
        col("key").cast("string").alias("kafka_key"),
        from_json(col("value").cast("string"), schema).alias("data"),
        col("timestamp").alias("kafka_ts"),
        lit(topic_name).alias("topic")
    ).filter(col("data").isNotNull()).select(
        col("topic"),
        col("data.*"),
        col("kafka_ts")
    )
    return parsed_df


def stream_topic_to_console(spark: SparkSession, topic_name: str, schema: StructType, 
                            kafka_bootstrap_servers: str):
    """Stream a Kafka topic to console."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [STREAM] Starting stream for topic: {topic_name}")
    
    # Read from Kafka
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", topic_name) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parse and format
    parsed_df = parse_kafka_stream(kafka_df, schema, topic_name)
    
    # Write to console
    query = parsed_df.writeStream \
        .format("console") \
        .outputMode("append") \
        .trigger(processingTime='2 seconds') \
        .option("truncate", "false") \
        .option("numRows", "100") \
        .start()
    
    return query


def main():
    """Main streaming function."""
    job_start_time = datetime.now()
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Streaming Job: Kafka → Console Display")
    print("=" * 80)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CONFIG] Kafka bootstrap servers: {Config.KAFKA_BOOTSTRAP_SERVERS}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Topics: events_views, events_clicks, events_ratings")
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
        
        # Stream each topic
        q1 = stream_topic_to_console(
            spark, 
            "events_views", 
            define_view_event_schema(), 
            Config.KAFKA_BOOTSTRAP_SERVERS
        )
        queries.append(q1)
        
        q2 = stream_topic_to_console(
            spark, 
            "events_clicks", 
            define_click_event_schema(), 
            Config.KAFKA_BOOTSTRAP_SERVERS
        )
        queries.append(q2)
        
        q3 = stream_topic_to_console(
            spark, 
            "events_ratings", 
            define_rating_event_schema(), 
            Config.KAFKA_BOOTSTRAP_SERVERS
        )
        queries.append(q3)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SUCCESS] All streaming queries started ({len(queries)} topics)")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Events will be displayed in the console every 2 seconds")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Press Ctrl+C to stop")
        print()
        print("=" * 80)
        
        # Wait for all queries (this blocks until stopped)
        for query in queries:
            query.awaitTermination()
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Stopping streaming queries...")
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

