# Streaming Pipeline Design

**Date**: 2025-12-17  
**Version**: 1.0

## Overview

This document describes the streaming pipeline architecture for ingesting real-time events from Kafka, processing them with Spark Structured Streaming, and writing to the Lakehouse Silver and Gold layers.

## Architecture

```
Kafka Topics
    ↓
Spark Structured Streaming (stream_kafka_to_silver.py)
    ↓
Silver Layer (events_views, events_clicks, events_ratings)
    ↓
Spark Structured Streaming (stream_trending_to_gold.py)
    ↓
Gold Layer (trending_now_1h, trending_now_24h)
```

## 1. Kafka Topics

### Topic Configuration

All topics are created automatically via the `kafka-topic-init` service in docker-compose, or manually using the Python initialization script.

**Topics:**
- `events_views` - View events (movie page views)
- `events_clicks` - Click events (user interactions)
- `events_ratings` - Rating events (user ratings)

**Topic Settings:**
- **Partitions**: 3 (for parallelism)
- **Replication Factor**: 1 (single broker setup)
- **Retention**: 
  - `events_views`: 7 days
  - `events_clicks`: 7 days
  - `events_ratings`: 30 days (more valuable data)

**Auto-Creation:**
- Kafka is configured with `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"`
- Topics will be auto-created on first message if they don't exist
- However, using the initialization service ensures proper partition/replication configuration

## 2. Event Schemas

### View Event (`events_views`)

**Required Fields:**
- `event_id` (string, UUID) - Unique event identifier
- `event_type` (string) - Must be "view"
- `event_ts` (string, ISO-8601) - Event timestamp in UTC
- `user_id` (integer) - User identifier
- `movie_id` (integer) - Movie identifier

**Optional Fields:**
- `session_id` (string, UUID) - Session identifier
- `device_type` (string) - Device type (mobile, desktop, etc.)
- `page_url` (string) - Page URL where view occurred

**Example:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "view",
  "event_ts": "2025-12-17T13:30:00.000Z",
  "user_id": 12345,
  "movie_id": 67890,
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "device_type": "mobile"
}
```

### Click Event (`events_clicks`)

**Required Fields:**
- `event_id` (string, UUID)
- `event_type` (string) - Must be "click"
- `event_ts` (string, ISO-8601)
- `user_id` (integer)
- `movie_id` (integer)

**Optional Fields:**
- `click_type` (string) - Type: "trailer", "poster", "title", "recommendation"
- `session_id` (string, UUID)
- `referrer` (string, URI) - Referrer URL

**Example:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440002",
  "event_type": "click",
  "event_ts": "2025-12-17T13:30:05.000Z",
  "user_id": 12345,
  "movie_id": 67890,
  "click_type": "trailer",
  "session_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

### Rating Event (`events_ratings`)

**Required Fields:**
- `event_id` (string, UUID)
- `event_type` (string) - Must be "rating"
- `event_ts` (string, ISO-8601)
- `user_id` (integer)
- `movie_id` (integer)
- `rating` (float) - Rating value (0.5 to 5.0, increments of 0.5)

**Optional Fields:**
- `review_text` (string) - Review text (max 5000 characters)

**Example:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440003",
  "event_type": "rating",
  "event_ts": "2025-12-17T13:30:10.000Z",
  "user_id": 12345,
  "movie_id": 67890,
  "rating": 4.5,
  "review_text": "Great movie!"
}
```

## 3. Silver Tables

### Table: `silver_events_views`

**Path**: `/data/silver/events_views`  
**Format**: Parquet (or Delta if configured)  
**Partition**: `event_date` (date derived from `event_ts`)

**Schema:**
- `event_id` (string) - UUID
- `event_ts` (timestamp) - Parsed from ISO-8601
- `user_id` (integer)
- `movie_id` (integer)
- `session_id` (string, nullable)
- `device_type` (string, nullable)
- `event_date` (date) - Partition column

**Uniqueness**: `event_id`

### Table: `silver_events_clicks`

**Path**: `/data/silver/events_clicks`  
**Format**: Parquet (or Delta if configured)  
**Partition**: `event_date`

**Schema:**
- `event_id` (string)
- `event_ts` (timestamp)
- `user_id` (integer)
- `movie_id` (integer)
- `click_type` (string, nullable)
- `session_id` (string, nullable)
- `referrer` (string, nullable)
- `event_date` (date)

**Uniqueness**: `event_id`

### Table: `silver_events_ratings`

**Path**: `/data/silver/events_ratings`  
**Format**: Parquet (or Delta if configured)  
**Partition**: `event_date`

**Schema:**
- `event_id` (string)
- `event_ts` (timestamp)
- `user_id` (integer)
- `movie_id` (integer)
- `rating` (float) - Validated to be 0.5-5.0
- `review_text` (string, nullable)
- `event_date` (date)

**Uniqueness**: `event_id`

## 4. Gold Tables

### Table: `trending_now_1h`

**Path**: `/data/gold/trending_now_1h`  
**Format**: Parquet (or Delta if configured)  
**Update Frequency**: Every 5 minutes  
**Window**: 1-hour rolling window

**Schema:**
- `window_ts` (timestamp) - Window end timestamp
- `movie_id` (integer)
- `views` (long) - Count of views in window
- `clicks` (long) - Count of clicks in window
- `trend_score` (double) - Computed score: `views * 1.0 + clicks * 2.0`

**Watermark**: 2 hours (allows late data up to 2h)

### Table: `trending_now_24h`

**Path**: `/data/gold/trending_now_24h`  
**Format**: Parquet (or Delta if configured)  
**Update Frequency**: Every 15 minutes  
**Window**: 24-hour rolling window, 1-hour slide

**Schema:**
- `window_ts` (timestamp) - Window end timestamp
- `movie_id` (integer)
- `views` (long)
- `clicks` (long)
- `trend_score` (double)

**Watermark**: 26 hours

## 5. Checkpointing

### Checkpoint Locations

All streaming queries use checkpointing for fault tolerance and exactly-once semantics.

**Kafka to Silver:**
- Main queries: `/data/_checkpoints/stream_kafka_to_silver/<topic>`
- Dead-letter queries: `/data/_checkpoints/stream_kafka_to_silver/<topic>_dlq`

**Trending to Gold:**
- 1h trending: `/data/_checkpoints/stream_trending_to_gold/trending_1h`
- 24h trending: `/data/_checkpoints/stream_trending_to_gold/trending_24h`

**Checkpoint Contents:**
- Offsets (for Kafka sources)
- State (for aggregations)
- Metadata (query progress, failures)

**Recovery:**
- On restart, streaming queries resume from last checkpoint
- No data loss if checkpoint directory is persisted (mounted volume)

## 6. Dead-Letter Handling

### Dead-Letter Tables

Invalid records (schema validation failures, parsing errors) are written to dead-letter tables:

**Path Pattern**: `/data/silver/_deadletter/<topic>`

**Schema:**
- `raw_payload` (string) - Original JSON payload
- `topic` (string) - Source Kafka topic
- `error_reason` (string) - Error description
- `error_ts` (timestamp) - When error occurred

**Example Reasons:**
- `schema_validation_failed` - JSON doesn't match expected schema
- `missing_required_field` - Required field is null/missing
- `invalid_timestamp` - Timestamp cannot be parsed
- `invalid_rating_value` - Rating outside valid range

**Monitoring:**
- Monitor dead-letter tables for data quality issues
- Set up alerts if dead-letter volume exceeds threshold

## 7. Environment Variables

### Required Variables

**KAFKA_BOOTSTRAP_SERVERS**
- Default: `kafka:29092`
- Description: Kafka broker addresses (comma-separated)

**LAKEHOUSE_PATH**
- Default: `/data`
- Description: Base path for lakehouse storage

**STORAGE_FORMAT**
- Default: `parquet`
- Options: `parquet`, `delta`
- Description: Storage format for Silver/Gold tables

**SPARK_MASTER**
- Default: `spark://spark-master:7077`
- Description: Spark master URL

### Optional Variables

**KAFKA_STARTING_OFFSETS**
- Default: `latest`
- Options: `earliest`, `latest`, or specific offset
- Description: Where to start reading from Kafka

## 8. Deployment

### Manual Submission

Streaming jobs are submitted manually using `spark-submit`:

**Kafka to Silver:**
```bash
docker-compose exec -e STORAGE_FORMAT=parquet \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  -e LAKEHOUSE_PATH=/data \
  spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
  /opt/spark/jobs/stream_kafka_to_silver.py
```

**Trending to Gold:**
```bash
docker-compose exec -e STORAGE_FORMAT=parquet \
  -e LAKEHOUSE_PATH=/data \
  spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
  /opt/spark/jobs/stream_trending_to_gold.py
```

### Airflow DAG

The `streaming_submit` DAG verifies job readiness and provides submission instructions. It does not automatically submit jobs (since `spark-submit` is not available in `airflow-worker`).

**Usage:**
1. Trigger the DAG manually in Airflow UI
2. Tasks will verify job scripts exist
3. Follow printed instructions to submit jobs manually

### Long-Running Services

For production, consider deploying streaming jobs as separate long-running services:

1. **Option 1**: Add streaming job containers to `docker-compose.yml` that run continuously
2. **Option 2**: Use Kubernetes/K8s jobs with restart policies
3. **Option 3**: Use a job scheduler (e.g., Airflow with SparkSubmitOperator if available)

## 9. Monitoring

### Spark UI

Monitor streaming applications via Spark Master UI:
- **URL**: http://localhost:8081
- **View**: Running Applications → Select application
- **Metrics**: 
  - Input rate (records/sec)
  - Processing rate
  - Batch duration
  - Total processed records

### Checkpoint Status

Check checkpoint directories to verify progress:
```bash
docker-compose exec spark-master ls -la /data/_checkpoints/stream_kafka_to_silver/
```

### Dead-Letter Monitoring

Monitor dead-letter tables for data quality:
```bash
docker-compose exec spark-master \
  /opt/spark/bin/spark-sql \
  --master spark://spark-master:7077 \
  -e "SELECT COUNT(*) FROM parquet.`/data/silver/_deadletter/events_views`"
```

## 10. Troubleshooting

### Streaming Job Not Processing

1. **Check Kafka connectivity**: Verify Kafka is running and topics exist
2. **Check Spark UI**: Verify application is running and has executors
3. **Check logs**: View Spark driver logs for errors
4. **Check checkpoint**: Verify checkpoint directory exists and is writable

### High Dead-Letter Volume

1. **Validate event schemas**: Ensure producers send valid JSON
2. **Check timestamp format**: Must be ISO-8601 UTC
3. **Review validation rules**: Check rating ranges, required fields

### Performance Issues

1. **Increase parallelism**: Add more Kafka partitions
2. **Tune Spark**: Adjust `spark.sql.shuffle.partitions`
3. **Check resource usage**: Monitor executor CPU/memory in Spark UI

## 11. Job Entrypoints

### Spark Jobs

**stream_kafka_to_silver.py**
- **Path**: `/opt/spark/jobs/stream_kafka_to_silver.py`
- **Entrypoint**: `main()` function
- **Env Vars**: `KAFKA_BOOTSTRAP_SERVERS`, `LAKEHOUSE_PATH`, `STORAGE_FORMAT`

**stream_trending_to_gold.py**
- **Path**: `/opt/spark/jobs/stream_trending_to_gold.py`
- **Entrypoint**: `main()` function
- **Env Vars**: `LAKEHOUSE_PATH`, `STORAGE_FORMAT`

### Submission Command Template

```bash
docker-compose exec \
  -e STORAGE_FORMAT=parquet \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  -e LAKEHOUSE_PATH=/data \
  spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
  /opt/spark/jobs/<job_script>.py
```

## Summary

- **Topics**: `events_views`, `events_clicks`, `events_ratings` (3 partitions each)
- **Silver Tables**: `events_views`, `events_clicks`, `events_ratings` (partitioned by `event_date`)
- **Gold Tables**: `trending_now_1h`, `trending_now_24h` (windowed aggregates)
- **Checkpoints**: `/data/_checkpoints/stream_*/`
- **Dead Letters**: `/data/silver/_deadletter/<topic>`
- **Deployment**: Manual via `spark-submit` or long-running services

