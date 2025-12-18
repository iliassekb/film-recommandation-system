"""
Airflow DAG for Recommendation Pipeline
Orchestrates ETL Bronze → Silver and ALS Training → Gold

Note: This DAG executes Spark jobs by connecting to the Spark cluster
via the Docker network. The jobs are executed in the Spark container.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import subprocess
import os
import sys


# Default arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2025, 1, 1),
}

# DAG definition
dag = DAG(
    'reco_pipeline',
    default_args=default_args,
    description='Recommendation Pipeline: ETL Bronze→Silver and ALS Training→Gold',
    schedule_interval=timedelta(days=1),  # Daily execution
    catchup=False,
    tags=['recommendation', 'etl', 'ml'],
)


def execute_spark_job(job_script: str, **context) -> None:
    """
    Execute a Spark job using PySpark programmatically.
    Creates a SparkSession and executes the job script directly.
    
    Args:
        job_script: Name of the job script (e.g., 'etl_bronze_to_silver.py')
        **context: Airflow context
    """
    spark_master = os.getenv('SPARK_MASTER', 'spark://spark-master:7077')
    lakehouse_path = os.getenv('LAKEHOUSE_PATH', '/data')
    # For our current Spark cluster image we use Parquet (no Delta jars available).
    # Default to parquet here so Airflow runs match the manual spark-submit that works.
    storage_format = os.getenv('STORAGE_FORMAT', 'parquet').lower()
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
    
    # Try multiple possible paths for job script
    job_paths = [
        f'/opt/spark/jobs/{job_script}',
        f'/opt/airflow/../spark/jobs/{job_script}',
        os.path.join(os.path.dirname(__file__), '..', '..', 'spark', 'jobs', job_script),
    ]
    
    job_path = None
    for path in job_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            job_path = abs_path
            break
    
    if not job_path:
        raise FileNotFoundError(
            f"Job script not found: {job_script}. Tried paths: {job_paths}"
        )
    
    print(f"[INFO] Executing Spark job: {job_script}")
    print(f"[INFO] Spark master: {spark_master}")
    print(f"[INFO] Job path: {job_path}")
    print(f"[INFO] Using PySpark programmatic execution")
    
    # Set environment variables
    os.environ['LAKEHOUSE_PATH'] = lakehouse_path
    os.environ['STORAGE_FORMAT'] = storage_format
    os.environ['MLFLOW_TRACKING_URI'] = mlflow_uri
    
    # Set JAVA_HOME if not set (required for PySpark)
    if 'JAVA_HOME' not in os.environ:
        # Try common Java locations (Debian/Ubuntu)
        java_home_candidates = [
            '/usr/lib/jvm/java-17-openjdk-amd64',  # OpenJDK 17 (installed)
            '/usr/lib/jvm/default-java',
            '/usr/lib/jvm/java-11-openjdk-amd64',
        ]
        for candidate in java_home_candidates:
            if os.path.exists(candidate):
                os.environ['JAVA_HOME'] = candidate
                print(f"[INFO] Set JAVA_HOME to: {candidate}")
                break
        else:
            # Fallback: try to find Java via which
            import shutil
            java_path = shutil.which('java')
            if java_path:
                # Extract JAVA_HOME from java path (e.g., /usr/lib/jvm/java-17-openjdk-amd64/bin/java)
                java_home = os.path.dirname(os.path.dirname(java_path))
                if os.path.exists(java_home):
                    os.environ['JAVA_HOME'] = java_home
                    print(f"[INFO] Set JAVA_HOME to: {java_home} (from java path)")
    
    try:
        from pyspark.sql import SparkSession
        from pyspark import SparkConf
        
        # Build Spark configuration
        conf = SparkConf()
        conf.setMaster(spark_master)
        conf.set('spark.sql.adaptive.enabled', 'true')
        conf.set('spark.sql.adaptive.coalescePartitions.enabled', 'true')
        conf.set('spark.app.name', f'airflow_{job_script}')
        
        # Delta Lake configuration
        if storage_format == 'delta':
            conf.set('spark.sql.extensions', 'io.delta.sql.DeltaSparkSessionExtension')
            conf.set('spark.sql.catalog.spark_catalog', 'org.apache.spark.sql.delta.catalog.DeltaCatalog')
            # Add Delta packages
            conf.set('spark.jars.packages', 'io.delta:delta-spark_2.12:3.0.0')
        
        # Add PyFiles for shared utilities
        conf.set('spark.submit.pyFiles', '/opt/spark/src/reco_platform')
        
        print(f"[INFO] Creating SparkSession with master: {spark_master}")
        
        # Create SparkSession
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        
        print(f"[INFO] SparkSession created successfully")
        print(f"[INFO] Spark version: {spark.version}")
        
        # Verify job script exists
        if not os.path.exists(job_path):
            raise FileNotFoundError(f"Job script not found: {job_path}")
        
        print(f"[INFO] Executing job script: {job_path}")
        
        # Read and execute the job script
        # We need to modify sys.path to include the src directory
        import sys
        src_path = '/opt/spark/src'
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        # Execute the job script
        with open(job_path, 'r') as f:
            job_code = f.read()
        
        # Execute in the current namespace with spark available
        exec_globals = {
            '__name__': '__main__',
            '__file__': job_path,
            'spark': spark,
        }
        exec(job_code, exec_globals)
        
        print(f"[SUCCESS] Job {job_script} completed successfully")
        
        # Stop SparkSession
        spark.stop()
        
    except ImportError as e:
        print(f"[ERROR] PySpark not available: {e}")
        print("[ERROR] Please install PySpark: pip install pyspark==3.5.0")
        raise
    except Exception as e:
        print(f"[ERROR] Job {job_script} failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def verify_silver_output(**context) -> None:
    """Verify that Silver tables exist after ETL."""
    import os
    from pathlib import Path
    
    lakehouse_path = os.getenv('LAKEHOUSE_PATH', '/data')
    silver_tables = ['ratings', 'movies', 'tags']
    
    print(f"[INFO] Verifying Silver layer outputs...")
    print(f"[INFO] Lakehouse path: {lakehouse_path}")
    
    all_exist = True
    for table in silver_tables:
        table_path = os.path.join(lakehouse_path, 'silver', table)
        if os.path.exists(table_path) or Path(table_path).exists():
            print(f"[OK] Silver table exists: {table_path}")
        else:
            print(f"[ERROR] Silver table missing: {table_path}")
            all_exist = False
    
    if not all_exist:
        raise FileNotFoundError("Some Silver tables are missing after ETL")
    
    print("[SUCCESS] All Silver tables verified")


def verify_gold_output(**context) -> None:
    """Verify that Gold tables exist after training."""
    import os
    from pathlib import Path
    
    lakehouse_path = os.getenv('LAKEHOUSE_PATH', '/data')
    gold_tables = ['recommendations_als']
    
    print(f"[INFO] Verifying Gold layer outputs...")
    print(f"[INFO] Lakehouse path: {lakehouse_path}")
    
    all_exist = True
    for table in gold_tables:
        table_path = os.path.join(lakehouse_path, 'gold', table)
        if os.path.exists(table_path) or Path(table_path).exists():
            print(f"[OK] Gold table exists: {table_path}")
        else:
            print(f"[ERROR] Gold table missing: {table_path}")
            all_exist = False
    
    # Also check for metrics
    metrics_path = os.path.join(lakehouse_path, 'gold', 'metrics')
    if os.path.exists(metrics_path):
        print(f"[OK] Metrics directory exists: {metrics_path}")
    else:
        print(f"[WARN] Metrics directory missing: {metrics_path}")
    
    if not all_exist:
        raise FileNotFoundError("Some Gold tables are missing after training")
    
    print("[SUCCESS] All Gold tables verified")


# Task 1: ETL Bronze → Silver
task_etl = PythonOperator(
    task_id='run_etl_bronze_to_silver',
    python_callable=execute_spark_job,
    op_kwargs={'job_script': 'etl_bronze_to_silver.py'},
    dag=dag,
)

# Task 2: Verify Silver output
task_verify_silver = PythonOperator(
    task_id='verify_silver_output',
    python_callable=verify_silver_output,
    dag=dag,
)

# Task 3: Train ALS and Generate Recommendations
task_train_als = PythonOperator(
    task_id='run_train_als_generate_recos',
    python_callable=execute_spark_job,
    op_kwargs={'job_script': 'train_als_and_generate_recos.py'},
    dag=dag,
)

# Task 4: Verify Gold output
task_verify_gold = PythonOperator(
    task_id='verify_gold_output',
    python_callable=verify_gold_output,
    dag=dag,
)

# Define task dependencies
task_etl >> task_verify_silver >> task_train_als >> task_verify_gold
