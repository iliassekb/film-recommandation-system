#!/usr/bin/env python3
"""
Python CLI tool for running pipeline jobs manually.
Provides commands: etl, train, validate
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from reco_platform.config import Config
from reco_platform.paths import (
    get_bronze_path, get_silver_path, get_gold_path,
    get_reports_path, get_models_path, get_metrics_path
)


def get_spark_submit_cmd(job_script: str) -> list[str]:
    """Build spark-submit command for a job."""
    spark_master = Config.SPARK_MASTER
    storage_format = Config.STORAGE_FORMAT
    
    cmd = [
        'spark-submit',
        '--master', spark_master,
        '--deploy-mode', 'client',
        '--conf', 'spark.sql.adaptive.enabled=true',
        '--conf', 'spark.sql.adaptive.coalescePartitions.enabled=true',
    ]
    
    if storage_format == 'delta':
        cmd.extend([
            '--packages', 'io.delta:delta-spark_2.12:3.0.0',
            '--conf', 'spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension',
            '--conf', 'spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog',
        ])
    
    # Add PyFiles for shared utilities
    project_root = Path(__file__).parent.parent
    src_path = project_root / 'src'
    if src_path.exists():
        # Add src to Python path via --py-files or PYTHONPATH
        cmd.append('--conf')
        cmd.append(f'spark.submit.pyFiles={src_path}')
    
    # Job script path
    job_path = project_root / 'spark' / 'jobs' / job_script
    if not job_path.exists():
        raise FileNotFoundError(f"Job script not found: {job_path}")
    
    cmd.append(str(job_path))
    
    return cmd


def run_etl(run_local: bool = False) -> None:
    """Run ETL job (Bronze → Silver)."""
    print("=" * 80)
    print("ETL Job: Bronze → Silver")
    print("=" * 80)
    
    cmd = get_spark_submit_cmd('etl_bronze_to_silver.py')
    
    print(f"[INFO] Lakehouse path: {Config.LAKEHOUSE_PATH}")
    print(f"[INFO] Storage format: {Config.STORAGE_FORMAT}")
    print()
    print("[INFO] Spark-submit command:")
    print(" ".join(cmd))
    print()
    
    if not run_local:
        print("[INFO] To execute this command, run it inside the Spark container:")
        print(f"  docker-compose exec spark-master {' '.join(cmd)}")
        print()
        print("[INFO] Or set RUN_LOCAL=1 to execute directly (requires Spark installed locally)")
        return
    
    print("[INFO] Executing ETL job...")
    
    env = os.environ.copy()
    env['LAKEHOUSE_PATH'] = Config.LAKEHOUSE_PATH
    env['STORAGE_FORMAT'] = Config.STORAGE_FORMAT
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            check=True
        )
        print("[SUCCESS] ETL job completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] ETL job failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("[ERROR] spark-submit not found. Please run inside Spark container or install Spark locally.")
        sys.exit(1)


def run_train(run_local: bool = False) -> None:
    """Run ALS training job."""
    print("=" * 80)
    print("ALS Training and Recommendations Generation")
    print("=" * 80)
    
    cmd = get_spark_submit_cmd('train_als_and_generate_recos.py')
    
    print(f"[INFO] Lakehouse path: {Config.LAKEHOUSE_PATH}")
    print(f"[INFO] Storage format: {Config.STORAGE_FORMAT}")
    print(f"[INFO] MLflow URI: {Config.MLFLOW_TRACKING_URI}")
    print(f"[INFO] ALS rank: {Config.ALS_RANK}")
    print(f"[INFO] ALS max iter: {Config.ALS_MAX_ITER}")
    print(f"[INFO] ALS reg param: {Config.ALS_REG_PARAM}")
    print(f"[INFO] Top-N: {Config.TOP_N}")
    print()
    print("[INFO] Spark-submit command:")
    print(" ".join(cmd))
    print()
    
    if not run_local:
        print("[INFO] To execute this command, run it inside the Spark container:")
        print(f"  docker-compose exec spark-master {' '.join(cmd)}")
        print()
        print("[INFO] Or set RUN_LOCAL=1 to execute directly (requires Spark installed locally)")
        return
    
    print("[INFO] Executing training job...")
    
    env = os.environ.copy()
    env['LAKEHOUSE_PATH'] = Config.LAKEHOUSE_PATH
    env['STORAGE_FORMAT'] = Config.STORAGE_FORMAT
    env['MLFLOW_TRACKING_URI'] = Config.MLFLOW_TRACKING_URI
    env['ALS_RANK'] = str(Config.ALS_RANK)
    env['ALS_MAX_ITER'] = str(Config.ALS_MAX_ITER)
    env['ALS_REG_PARAM'] = str(Config.ALS_REG_PARAM)
    env['TOP_N'] = str(Config.TOP_N)
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            check=True
        )
        print("[SUCCESS] Training job completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Training job failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("[ERROR] spark-submit not found. Please run inside Spark container or install Spark locally.")
        sys.exit(1)


def validate() -> None:
    """Validate Bronze/Silver/Gold layer presence."""
    print("=" * 80)
    print("Validation: Checking Bronze/Silver/Gold Layers")
    print("=" * 80)
    
    lakehouse_path = Config.LAKEHOUSE_PATH
    print(f"[INFO] Lakehouse path: {lakehouse_path}")
    print()
    
    all_ok = True
    
    # Check Bronze
    print("[INFO] Checking Bronze layer...")
    bronze_path = get_bronze_path()
    bronze_files = ['ratings.csv', 'movies.csv', 'tags.csv']
    
    for file in bronze_files:
        file_path = os.path.join(bronze_path, file)
        if os.path.exists(file_path) or Path(file_path).exists():
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            print(f"  [OK] {file} ({size:,} bytes)")
        else:
            print(f"  [ERROR] {file} not found")
            all_ok = False
    
    # Check Silver
    print()
    print("[INFO] Checking Silver layer...")
    silver_tables = ['ratings', 'movies', 'tags']
    
    for table in silver_tables:
        table_path = get_silver_path(table)
        if os.path.exists(table_path) or Path(table_path).exists():
            print(f"  [OK] {table} exists at {table_path}")
        else:
            print(f"  [ERROR] {table} not found at {table_path}")
            all_ok = False
    
    # Check reports
    reports_path = get_reports_path('silver')
    if os.path.exists(reports_path):
        report_files = list(Path(reports_path).glob('*.json'))
        print(f"  [OK] Reports directory exists ({len(report_files)} reports)")
    else:
        print(f"  [WARN] Reports directory not found: {reports_path}")
    
    # Check Gold
    print()
    print("[INFO] Checking Gold layer...")
    gold_tables = ['recommendations_als']
    
    for table in gold_tables:
        table_path = get_gold_path(table)
        if os.path.exists(table_path) or Path(table_path).exists():
            print(f"  [OK] {table} exists at {table_path}")
        else:
            print(f"  [WARN] {table} not found at {table_path} (may not be generated yet)")
    
    # Check models
    models_base = get_models_path('als')
    if os.path.exists(models_base):
        model_versions = [d for d in os.listdir(models_base) if os.path.isdir(os.path.join(models_base, d))]
        print(f"  [OK] Models directory exists ({len(model_versions)} versions)")
    else:
        print(f"  [WARN] Models directory not found: {models_base}")
    
    # Check metrics
    metrics_path = get_metrics_path()
    if os.path.exists(metrics_path):
        metric_files = list(Path(metrics_path).glob('*.json'))
        print(f"  [OK] Metrics directory exists ({len(metric_files)} metric files)")
    else:
        print(f"  [WARN] Metrics directory not found: {metrics_path}")
    
    print()
    if all_ok:
        print("[SUCCESS] Validation passed!")
    else:
        print("[ERROR] Validation failed - some required files/tables are missing")
        sys.exit(1)


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description='Run recommendation pipeline jobs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Print ETL command (don't execute)
  python tools/run_pipeline.py etl

  # Execute ETL locally (requires Spark)
  RUN_LOCAL=1 python tools/run_pipeline.py etl

  # Execute ETL in Docker container
  docker-compose exec spark-master spark-submit --master spark://spark-master:7077 spark/jobs/etl_bronze_to_silver.py

  # Validate layers
  python tools/run_pipeline.py validate
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # ETL command
    etl_parser = subparsers.add_parser('etl', help='Run ETL job (Bronze → Silver)')
    etl_parser.add_argument(
        '--run-local',
        action='store_true',
        help='Execute locally (requires Spark installed). Default: print command only.'
    )
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Run ALS training job')
    train_parser.add_argument(
        '--run-local',
        action='store_true',
        help='Execute locally (requires Spark installed). Default: print command only.'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate Bronze/Silver/Gold layers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    run_local = os.getenv('RUN_LOCAL', '0') == '1' or getattr(args, 'run_local', False)
    
    if args.command == 'etl':
        run_etl(run_local=run_local)
    elif args.command == 'train':
        run_train(run_local=run_local)
    elif args.command == 'validate':
        validate()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()







