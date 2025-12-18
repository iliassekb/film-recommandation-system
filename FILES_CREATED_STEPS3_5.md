# Files Created for Steps 3-5

This document lists all files created for Steps 3, 4, and 5 of the recommendation pipeline.

## Shared Utilities (`src/reco_platform/`)

1. **`src/reco_platform/__init__.py`**
   - Package initialization

2. **`src/reco_platform/config.py`**
   - Configuration class reading environment variables
   - Lakehouse paths, storage format, MLflow, ALS hyperparameters

3. **`src/reco_platform/paths.py`**
   - Path utilities for Bronze/Silver/Gold layers
   - Functions: `get_bronze_path()`, `get_silver_path()`, `get_gold_path()`, etc.

4. **`src/reco_platform/io.py`**
   - I/O utilities for reading/writing Delta/Parquet
   - Functions: `read_table()`, `write_table()`, `read_csv_with_schema()`, `table_exists()`

5. **`src/reco_platform/quality.py`**
   - Data quality validation utilities
   - Classes: `QualityReport`
   - Functions: `check_null_percentage()`, `check_value_range()`, `check_duplicates()`, validation functions for ratings/movies/tags

## Spark Jobs (`spark/jobs/`)

6. **`spark/jobs/etl_bronze_to_silver.py`**
   - ETL job: Bronze → Silver
   - Processes: ratings.csv, movies.csv, tags.csv
   - Cleaning rules, validation, quality reports
   - Outputs: Silver tables + JSON reports

7. **`spark/jobs/train_als_and_generate_recos.py`**
   - ALS training and recommendations generation
   - Time-based train/test split
   - Model evaluation (RMSE)
   - Top-N recommendations for all users
   - MLflow integration (optional)
   - Outputs: Gold recommendations, model artifacts, metrics JSON

## Airflow DAG (`airflow/dags/`)

8. **`airflow/dags/reco_pipeline_dag.py`**
   - Airflow DAG: `reco_pipeline`
   - Tasks:
     - `run_etl_bronze_to_silver`
     - `verify_silver_output`
     - `run_train_als_generate_recos`
     - `verify_gold_output`
   - Executes Spark jobs via `docker exec` in spark-master container

## CLI Tools (`tools/`)

9. **`tools/run_pipeline.py`**
   - Python CLI for running pipeline jobs
   - Commands:
     - `etl`: Run ETL job (prints command or executes if RUN_LOCAL=1)
     - `train`: Run training job (prints command or executes if RUN_LOCAL=1)
     - `validate`: Validate Bronze/Silver/Gold layers

## Documentation (`docs/`)

10. **`docs/03_step3_to_step5.md`**
    - Complete documentation for Steps 3-5
    - How to run jobs via Airflow and CLI
    - Expected output structures
    - Troubleshooting guide

## Updated Files

11. **`README.md`**
    - Added Steps 3-5 quick start section
    - Updated "Next Steps" to reflect completion

12. **`docker-compose.yml`**
    - Added volume mounts for Spark jobs and shared utilities:
      - `./spark/jobs:/opt/spark/jobs`
      - `./src:/opt/spark/src`
      - `./lakehouse:/data` (additional mount for /data path)

## Summary

- **Total files created**: 10 new files
- **Total files updated**: 2 files
- **Lines of code**: ~2000+ lines
- **Documentation**: Complete guide for Steps 3-5

All files follow:
- ✅ snake_case naming convention
- ✅ Python-only (no shell scripts)
- ✅ Environment variable configuration
- ✅ Clear logging and error handling
- ✅ Data quality checks
- ✅ Cross-platform compatibility







