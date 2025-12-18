#!/bin/bash
# Wrapper script to run Spark job in Spark container
# This script should be executed from Airflow and will connect to Spark via network

set -e

JOB_SCRIPT=$1
SPARK_MASTER=${SPARK_MASTER:-spark://spark-master:7077}
LAKEHOUSE_PATH=${LAKEHOUSE_PATH:-/data}
STORAGE_FORMAT=${STORAGE_FORMAT:-delta}
MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI:-http://mlflow:5000}

JOB_PATH="/opt/spark/jobs/${JOB_SCRIPT}"

echo "[INFO] Executing Spark job: ${JOB_SCRIPT}"
echo "[INFO] Spark master: ${SPARK_MASTER}"
echo "[INFO] Job path: ${JOB_PATH}"
echo "[INFO] Lakehouse path: ${LAKEHOUSE_PATH}"

# Build spark-submit command
SPARK_CMD="spark-submit \
  --master ${SPARK_MASTER} \
  --deploy-mode client \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.adaptive.coalescePartitions.enabled=true"

if [ "${STORAGE_FORMAT}" = "delta" ]; then
  SPARK_CMD="${SPARK_CMD} \
    --packages io.delta:delta-spark_2.12:3.0.0 \
    --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
    --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog"
fi

SPARK_CMD="${SPARK_CMD} \
  --py-files /opt/spark/src/reco_platform \
  ${JOB_PATH}"

# Export environment variables
export LAKEHOUSE_PATH
export STORAGE_FORMAT
export MLFLOW_TRACKING_URI

# Try to find spark-submit
if command -v spark-submit &> /dev/null; then
  echo "[INFO] Using spark-submit from PATH"
  eval "${SPARK_CMD}"
elif [ -f "/opt/spark/bin/spark-submit" ]; then
  echo "[INFO] Using /opt/spark/bin/spark-submit"
  /opt/spark/bin/spark-submit \
    --master ${SPARK_MASTER} \
    --deploy-mode client \
    --conf spark.sql.adaptive.enabled=true \
    --conf spark.sql.adaptive.coalescePartitions.enabled=true \
    ${STORAGE_FORMAT_OPTS} \
    --py-files /opt/spark/src/reco_platform \
    ${JOB_PATH}
else
  echo "[ERROR] spark-submit not found. Please ensure Spark is installed or available in PATH."
  exit 1
fi







