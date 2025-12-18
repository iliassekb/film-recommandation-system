# Steps 3-5: ETL, ALS Training, and Orchestration

This document describes the implementation of Steps 3, 4, and 5 of the recommendation pipeline.

## Overview

- **Step 3**: Spark ETL to transform Bronze → Silver (data cleaning and validation)
- **Step 4**: ALS model training and recommendations generation (Silver → Gold)
- **Step 5**: Airflow orchestration of the complete pipeline

## Architecture

```
Bronze (CSV) → [ETL] → Silver (Delta/Parquet) → [ALS Training] → Gold (Delta/Parquet)
                                                      ↓
                                              Recommendations + Metrics
```

## Step 3: ETL Bronze → Silver

### Job: `spark/jobs/etl_bronze_to_silver.py`

**Purpose**: Clean and validate MovieLens data from Bronze layer, write to Silver layer.

**Inputs**:
- Bronze: `/data/bronze/movielens/ml-25m/ratings.csv`
- Bronze: `/data/bronze/movielens/ml-25m/movies.csv`
- Bronze: `/data/bronze/movielens/ml-25m/tags.csv` (optional)

**Outputs**:
- Silver: `/data/silver/ratings` (partitioned by year, month)
- Silver: `/data/silver/movies`
- Silver: `/data/silver/tags` (partitioned by year, month)
- Reports: `/data/silver/_reports/etl_bronze_to_silver_report_*.json`

### Data Cleaning Rules

1. **Ratings**:
   - Drop null `user_id` or `movie_id`
   - Filter ratings within 0.5-5.0 range
   - Deduplicate by (`user_id`, `movie_id`, `rating_ts`)
   - Convert Unix timestamp to `timestamp` type
   - Partition by `year` and `month` of `rating_ts`

2. **Movies**:
   - Drop null `movie_id` or `title`
   - Extract `release_year` from title (format: "Title (YYYY)")
   - Split `genres` string into array
   - Deduplicate by `movie_id`

3. **Tags**:
   - Drop null `user_id`, `movie_id`, or `tag`
   - Convert Unix timestamp to `timestamp` type
   - Partition by `year` and `month` of `tag_ts`

### Quality Checks

- Null percentage checks (must be 0% for required fields)
- Value range validation (ratings 0.5-5.0)
- Duplicate detection
- Row count validation

### Running the ETL Job

**Via Airflow** (recommended):
1. Open Airflow UI: http://localhost:8082
2. Login: admin/admin
3. Find DAG: `reco_pipeline`
4. Trigger DAG manually or wait for scheduled execution
5. Monitor task: `run_etl_bronze_to_silver`

**Via Python CLI**:
```bash
# Print command (don't execute)
python tools/run_pipeline.py etl

# Execute in Spark container
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages io.delta:delta-spark_2.12:3.0.0 \
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
  /opt/spark/jobs/etl_bronze_to_silver.py
```

**Via Python CLI (local execution)**:
```bash
RUN_LOCAL=1 python tools/run_pipeline.py etl
```

### Expected Output Structure

```
/data/silver/
├── ratings/
│   ├── year=2000/
│   │   ├── month=1/
│   │   │   └── part-*.parquet (or delta files)
│   │   └── month=2/
│   └── year=2001/
├── movies/
│   └── part-*.parquet (or delta files)
├── tags/
│   └── year=2000/
│       └── month=1/
└── _reports/
    ├── etl_bronze_to_silver_report_20250101_120000.json
    ├── quality_ratings_20250101_120000.json
    ├── quality_movies_20250101_120000.json
    └── quality_tags_20250101_120000.json
```

### Sample Silver Schema

**ratings**:
- `user_id` (int)
- `movie_id` (int)
- `rating` (float)
- `rating_ts` (timestamp)
- `year` (int, partition)
- `month` (int, partition)

**movies**:
- `movie_id` (int)
- `title` (string)
- `genres_string` (string)
- `genres` (array<string>)
- `release_year` (int, nullable)

**tags**:
- `user_id` (int)
- `movie_id` (int)
- `tag` (string)
- `tag_ts` (timestamp)
- `year` (int, partition)
- `month` (int, partition)

---

## Step 4: ALS Training and Recommendations

### Job: `spark/jobs/train_als_and_generate_recos.py`

**Purpose**: Train ALS model on Silver ratings, evaluate, and generate Top-N recommendations.

**Inputs**:
- Silver: `/data/silver/ratings`

**Outputs**:
- Gold: `/data/gold/recommendations_als`
- Gold: `/data/gold/models/als/<model_version>/`
- Gold: `/data/gold/metrics/run_metrics_<model_version>.json`
- MLflow: Experiment logged (if MLflow available)

### Training Process

1. **Data Split**: Time-based split (80% train, 20% test) using `rating_ts`
2. **ALS Training**:
   - Hyperparameters from environment:
     - `ALS_RANK` (default: 50)
     - `ALS_MAX_ITER` (default: 10)
     - `ALS_REG_PARAM` (default: 0.1)
     - `ALS_COLD_START_STRATEGY` (default: "drop")
3. **Evaluation**: RMSE on test set
4. **Recommendations**: Top-N for all users (N from `TOP_N` env, default: 10)

### Recommendations Schema

**recommendations_als**:
- `user_id` (int)
- `recommendations` (array<struct<movie_id:int, score:float, rank:int>>)
- `model_version` (string, e.g., "20250101_120000")
- `generated_ts` (timestamp)

### Running the Training Job

**Via Airflow**:
1. Open Airflow UI: http://localhost:8082
2. Find DAG: `reco_pipeline`
3. Task: `run_train_als_generate_recos` (runs after ETL)

**Via Python CLI**:
```bash
# Print command
python tools/run_pipeline.py train

# Execute in Spark container
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages io.delta:delta-spark_2.12:3.0.0 \
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
  /opt/spark/jobs/train_als_and_generate_recos.py
```

**Via Python CLI (local execution)**:
```bash
RUN_LOCAL=1 python tools/run_pipeline.py train
```

### Expected Output Structure

```
/data/gold/
├── recommendations_als/
│   └── part-*.parquet (or delta files)
├── models/
│   └── als/
│       └── 20250101_120000/
│           ├── metadata/
│           ├── data/
│           └── ...
└── metrics/
    └── run_metrics_20250101_120000.json
```

### Metrics JSON Format

```json
{
  "model_version": "20250101_120000",
  "execution_ts": "2025-01-01T12:00:00Z",
  "hyperparameters": {
    "rank": 50,
    "max_iter": 10,
    "reg_param": 0.1,
    "cold_start_strategy": "drop"
  },
  "dataset_info": {
    "storage_format": "delta",
    "split_info": {
      "train_count": 20000000,
      "test_count": 5000000,
      "total_count": 25000000
    }
  },
  "evaluation": {
    "rmse": 0.8523,
    "test_count": 5000000,
    "predictions_count": 4800000,
    "coverage": 0.96
  },
  "recommendations": {
    "top_n": 10
  }
}
```

### MLflow Integration

If MLflow is available and `MLFLOW_TRACKING_URI` is set:
- Parameters logged: `rank`, `max_iter`, `reg_param`, `cold_start_strategy`, `top_n`
- Metrics logged: `rmse`, `test_count`, `predictions_count`, `coverage`
- Model artifact: Saved to MLflow
- Metrics JSON: Logged as artifact

If MLflow is unavailable, training continues with a warning.

---

## Step 5: Airflow Orchestration

### DAG: `reco_pipeline`

**Location**: `airflow/dags/reco_pipeline_dag.py`

**Schedule**: Daily (configurable)

**Tasks**:
1. `run_etl_bronze_to_silver`: Execute ETL job
2. `verify_silver_output`: Verify Silver tables exist
3. `run_train_als_generate_recos`: Train ALS and generate recommendations
4. `verify_gold_output`: Verify Gold tables exist

**Dependencies**:
```
run_etl_bronze_to_silver → verify_silver_output → run_train_als_generate_recos → verify_gold_output
```

### Triggering the DAG

**Via Airflow UI**:
1. Open http://localhost:8082
2. Login: admin/admin
3. Find DAG: `reco_pipeline`
4. Click "Play" button to trigger manually
5. Monitor execution in Graph/Tree view

**Via Airflow CLI** (inside container):
```bash
docker-compose exec airflow-scheduler airflow dags trigger reco_pipeline
```

### DAG Configuration

The DAG uses PythonOperator to execute Spark jobs via `docker exec` in the `spark-master` container. This ensures:
- Spark jobs run in the correct environment
- Shared utilities (`src/reco_platform`) are accessible
- Lakehouse paths are consistent

### Environment Variables

Set in `docker-compose.yml` or Airflow connections:
- `LAKEHOUSE_PATH`: Default `/data` (or `/lakehouse` if mounted differently)
- `STORAGE_FORMAT`: `delta` or `parquet` (default: `delta`)
- `MLFLOW_TRACKING_URI`: Default `http://mlflow:5000`
- `ALS_RANK`: Default `50`
- `ALS_MAX_ITER`: Default `10`
- `ALS_REG_PARAM`: Default `0.1`
- `TOP_N`: Default `10`

---

## Validation

### Validate Layers

Use the Python CLI to validate Bronze/Silver/Gold layers:

```bash
python tools/run_pipeline.py validate
```

This checks:
- Bronze: Required CSV files exist
- Silver: Tables exist (`ratings`, `movies`, `tags`)
- Gold: Tables exist (`recommendations_als`)
- Reports: Quality reports present
- Models: Model versions saved
- Metrics: Metrics JSON files present

### Expected Output

```
================================================================================
Validation: Checking Bronze/Silver/Gold Layers
================================================================================
[INFO] Lakehouse path: /data
[INFO] Checking Bronze layer...
  [OK] ratings.csv (1,234,567,890 bytes)
  [OK] movies.csv (12,345,678 bytes)
  [OK] tags.csv (123,456,789 bytes)

[INFO] Checking Silver layer...
  [OK] ratings exists at /data/silver/ratings
  [OK] movies exists at /data/silver/movies
  [OK] tags exists at /data/silver/tags
  [OK] Reports directory exists (4 reports)

[INFO] Checking Gold layer...
  [OK] recommendations_als exists at /data/gold/recommendations_als
  [OK] Models directory exists (1 versions)
  [OK] Metrics directory exists (1 metric files)

[SUCCESS] Validation passed!
```

---

## Troubleshooting

### ETL Job Fails

1. **Check Bronze data exists**:
   ```bash
   docker-compose exec spark-master ls -lh /data/bronze/movielens/ml-25m/
   ```

2. **Check logs**:
   ```bash
   docker-compose logs spark-master
   ```

3. **Verify environment variables**:
   ```bash
   docker-compose exec spark-master env | grep LAKEHOUSE_PATH
   ```

### Training Job Fails

1. **Check Silver data exists**:
   ```bash
   docker-compose exec spark-master ls -lh /data/silver/ratings/
   ```

2. **Check MLflow connection**:
   ```bash
   curl http://localhost:5000/health
   ```

3. **Verify memory settings** (if OOM errors):
   - Increase Spark executor memory in `docker-compose.yml`

### Airflow DAG Not Appearing

1. **Check DAG file syntax**:
   ```bash
   docker-compose exec airflow-scheduler python -m py_compile /opt/airflow/dags/reco_pipeline_dag.py
   ```

2. **Check Airflow logs**:
   ```bash
   docker-compose logs airflow-scheduler | grep reco_pipeline
   ```

3. **Refresh DAGs**:
   - Airflow UI: Admin → Refresh DAGs
   - Or restart scheduler: `docker-compose restart airflow-scheduler`

### Storage Format Issues

If using Delta Lake, ensure:
- Delta Spark package is included: `io.delta:delta-spark_2.12:3.0.0`
- Spark extensions configured correctly
- Delta tables are not corrupted (check with `DESCRIBE DETAIL`)

---

## Next Steps

After Steps 3-5 are complete:
- ✅ Bronze layer bootstrapped
- ✅ Silver layer cleaned and validated
- ✅ Gold layer with recommendations
- ⏭️ **Step 6**: Streaming ingestion (Kafka → Bronze/Silver)
- ⏭️ **Step 7**: API endpoints for serving recommendations
- ⏭️ **Step 8**: Real-time trending detection

---

**Last Updated**: January 2025

