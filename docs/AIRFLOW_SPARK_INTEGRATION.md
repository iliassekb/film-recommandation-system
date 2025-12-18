# Airflow-Spark Integration Guide

## Problem

The Airflow worker container cannot execute `docker exec` commands because it doesn't have access to the Docker socket. This prevents direct execution of Spark jobs from Airflow.

## Solution

We use **PySpark** installed in the Airflow container to submit jobs programmatically to the Spark cluster via the Docker network.

## Architecture

```
Airflow Container (with PySpark)
    ↓ (via Docker network)
Spark Master (spark://spark-master:7077)
    ↓
Spark Workers
    ↓
Lakehouse (/data)
```

## Implementation

### 1. Install PySpark in Airflow

The `requirements.txt` in `airflow/config/` includes:
- `pyspark==3.5.0`
- `delta-spark==3.0.0`

These are installed when the Airflow containers start.

### 2. DAG Execution

The DAG uses `PythonOperator` to:
1. Create a SparkSession connected to `spark://spark-master:7077`
2. Execute the job script programmatically
3. Handle errors and logging

### 3. Job Scripts Location

Job scripts are mounted at `/opt/spark/jobs/` in both Airflow and Spark containers:
- `etl_bronze_to_silver.py`
- `train_als_and_generate_recos.py`

### 4. Shared Utilities

The `src/reco_platform` module is mounted at `/opt/spark/src/` and available to both containers.

## Environment Variables

Set in `docker-compose.yml`:
- `LAKEHOUSE_PATH=/data`
- `STORAGE_FORMAT=delta`
- `MLFLOW_TRACKING_URI=http://mlflow:5000`
- `SPARK_MASTER=spark://spark-master:7077`

## Troubleshooting

### PySpark not found

If you see "pyspark not found" errors:
1. Check that `requirements.txt` is mounted correctly
2. Check container logs: `docker-compose logs airflow-worker`
3. Manually install: `docker-compose exec airflow-worker pip install pyspark==3.5.0`

### Cannot connect to Spark Master

If connection to Spark fails:
1. Verify Spark is running: `docker-compose ps spark-master`
2. Check network: `docker-compose exec airflow-worker ping spark-master`
3. Verify Spark master URL: `spark://spark-master:7077`

### Job scripts not found

If job scripts are missing:
1. Verify volumes are mounted: `docker-compose exec airflow-worker ls -la /opt/spark/jobs/`
2. Check docker-compose.yml volumes section
3. Restart containers: `docker-compose restart airflow-scheduler airflow-worker`

## Alternative Approaches

If PySpark doesn't work, alternatives include:

1. **Docker Socket Mount** (not recommended for production):
   ```yaml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock
   ```

2. **Spark REST API** (if enabled):
   - Submit jobs via HTTP REST API
   - Requires Spark 3.0+ with REST API enabled

3. **Message Queue** (Redis/Kafka):
   - Airflow publishes job requests
   - Spark consumer executes jobs
   - More complex but scalable

## Current Status

✅ PySpark installed in Airflow containers
✅ Jobs executed programmatically via SparkSession
✅ Network connectivity verified
✅ Volumes mounted correctly







