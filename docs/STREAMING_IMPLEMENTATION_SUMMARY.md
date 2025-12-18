# Streaming Pipeline Implementation Summary

**Date**: 2025-12-17  
**Implementation**: Complete

## Files Created

### Monitoring (PART 1)
1. `api/main.py` - Modified: Added Prometheus metrics middleware and `/metrics` endpoint
2. `api/requirements.txt` - Modified: Added `prometheus-client==0.19.0`
3. `prometheus/prometheus.yml` - Modified: Updated FastAPI scrape config
4. `grafana/dashboards/api-overview.json` - Created: API monitoring dashboard
5. `grafana/dashboards/platform-overview.json` - Created: Platform overview dashboard
6. `docs/05_monitoring_audit.md` - Created: Monitoring audit report

### Streaming Pipeline (PART 2)
7. `tools/kafka_topic_init.py` - Created: Kafka topic initialization script (Python, no shell scripts)
8. `docker-compose.yml` - Modified: Added `kafka-topic-init` service
9. `spark/jobs/stream_kafka_to_silver.py` - Created: Kafka → Silver streaming job
10. `spark/jobs/stream_trending_to_gold.py` - Created: Silver → Gold trending aggregation job
11. `airflow/dags/streaming_submit_dag.py` - Created: Airflow DAG for streaming job verification
12. `src/reco_platform/config.py` - Modified: Added `KAFKA_BOOTSTRAP_SERVERS` config
13. `airflow/config/requirements.txt` - Modified: Added `requests==2.31.0`
14. `docs/06_streaming_design.md` - Created: Streaming pipeline design documentation

## PART 1: Prometheus + Grafana Verification & Fixes

### Status: ✅ OPERATIONAL

**Prometheus:**
- **Service**: `prometheus` on port `9090`
- **Scrapes**: `fastapi:8000/metrics` (NEW - verified and configured)
- **Config**: `prometheus/prometheus.yml` (updated)

**Grafana:**
- **Service**: `grafana` on port `3000`
- **Credentials**: `admin` / `admin`
- **Datasource**: Prometheus auto-provisioned at `http://prometheus:9090`
- **Dashboards**: 
  - API Overview (`api-overview.json`) - RPS, P95 latency, error rate, top endpoints
  - Platform Overview (`platform-overview.json`) - API stats, request distribution, latency heatmap

**FastAPI Metrics:**
- **Endpoint**: `/metrics` (Prometheus format)
- **Metrics**: 
  - `http_requests_total` (Counter) - Labels: method, endpoint, status
  - `http_request_duration_seconds` (Histogram) - Labels: method, endpoint
- **Middleware**: Automatic tracking of all HTTP requests

**Access URLs:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- FastAPI Metrics: http://localhost:8000/metrics

## PART 2: Streaming Pipeline Implementation

### Kafka Topics

**Topics Created:**
- `events_views` (3 partitions, 7-day retention)
- `events_clicks` (3 partitions, 7-day retention)
- `events_ratings` (3 partitions, 30-day retention)

**Initialization:**
- Service: `kafka-topic-init` (runs once on startup)
- Script: `tools/kafka_topic_init.py` (Python, no shell scripts)
- Auto-creation: Also enabled via `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"`

### Spark Streaming Jobs

**Job 1: `stream_kafka_to_silver.py`**
- **Entrypoint**: `/opt/spark/jobs/stream_kafka_to_silver.py`
- **Function**: `main()`
- **Reads**: Kafka topics `events_views`, `events_clicks`, `events_ratings`
- **Writes**: 
  - Silver: `/data/silver/events_views`, `/data/silver/events_clicks`, `/data/silver/events_ratings`
  - Dead-letter: `/data/silver/_deadletter/<topic>`
- **Checkpoints**: `/data/_checkpoints/stream_kafka_to_silver/<topic>`
- **Env Vars**: `KAFKA_BOOTSTRAP_SERVERS`, `LAKEHOUSE_PATH`, `STORAGE_FORMAT`

**Job 2: `stream_trending_to_gold.py`**
- **Entrypoint**: `/opt/spark/jobs/stream_trending_to_gold.py`
- **Function**: `main()`
- **Reads**: Silver event tables (`events_views`, `events_clicks`)
- **Writes**: 
  - Gold: `/data/gold/trending_now_1h` (5-min updates, 1h window)
  - Gold: `/data/gold/trending_now_24h` (15-min updates, 24h window)
- **Checkpoints**: `/data/_checkpoints/stream_trending_to_gold/<window>`
- **Env Vars**: `LAKEHOUSE_PATH`, `STORAGE_FORMAT`

### Airflow DAG

**DAG**: `streaming_submit`
- **File**: `airflow/dags/streaming_submit_dag.py`
- **Schedule**: Manual trigger only
- **Tasks**:
  1. `verify_kafka_silver_ready` - Verifies `stream_kafka_to_silver.py` exists
  2. `verify_kafka_silver_running` - Checks if app is running in Spark cluster
  3. `verify_trending_gold_ready` - Verifies `stream_trending_to_gold.py` exists
  4. `verify_trending_gold_running` - Checks if app is running in Spark cluster

**Note**: DAG provides submission instructions but does not auto-submit (since `spark-submit` is not available in `airflow-worker`). Jobs must be submitted manually or deployed as long-running services.

### Submission Commands

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

## Environment Variables Summary

### Required for Streaming Jobs

- **KAFKA_BOOTSTRAP_SERVERS**: `kafka:29092` (default)
- **LAKEHOUSE_PATH**: `/data` (default)
- **STORAGE_FORMAT**: `parquet` (default, or `delta` if Delta jars available)
- **SPARK_MASTER**: `spark://spark-master:7077` (default)

### Prometheus Scrape Targets

- **fastapi:8000/metrics** - FastAPI application metrics ✅
- Other targets (kafka, spark-master, etc.) may require exporters for detailed metrics

## Next Steps

1. **Start Services**: `docker-compose up -d` (includes `kafka-topic-init`)
2. **Verify Topics**: Check Kafka UI at http://localhost:8080
3. **Submit Streaming Jobs**: Use commands above or follow Airflow DAG instructions
4. **Monitor**: 
   - Spark UI: http://localhost:8081
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090

## Documentation

- **Monitoring Audit**: `docs/05_monitoring_audit.md`
- **Streaming Design**: `docs/06_streaming_design.md`




