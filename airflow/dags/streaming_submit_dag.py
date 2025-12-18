"""
Airflow DAG for Streaming Pipeline Submission
Submits Spark Structured Streaming jobs to the Spark cluster.
These are long-running streaming applications that run continuously.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os


# Default arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'start_date': datetime(2025, 1, 1),
}

# DAG definition
dag = DAG(
    'streaming_submit',
    default_args=default_args,
    description='Submit Spark Structured Streaming jobs to cluster',
    schedule_interval=None,  # Manual trigger only - streaming jobs run continuously
    catchup=False,
    tags=['streaming', 'kafka', 'spark'],
)


def verify_streaming_job_ready(job_script: str, **context) -> None:
    """
    Verify that streaming job script exists and provide submission instructions.
    Since airflow-worker doesn't have direct access to spark-submit,
    this task verifies readiness and documents how to submit manually.
    
    Args:
        job_script: Name of the streaming job script
        **context: Airflow context
    """
    spark_master = os.getenv('SPARK_MASTER', 'spark://spark-master:7077')
    lakehouse_path = os.getenv('LAKEHOUSE_PATH', '/data')
    storage_format = os.getenv('STORAGE_FORMAT', 'parquet')
    kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    
    # Job script path
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
        raise FileNotFoundError(f"Job script not found: {job_script}. Tried paths: {job_paths}")
    
    print(f"[SUCCESS] Streaming job script found: {job_path}")
    print(f"[INFO] Job: {job_script}")
    print(f"[INFO] Spark master: {spark_master}")
    print(f"[INFO] Storage format: {storage_format}")
    print(f"[INFO] Kafka bootstrap servers: {kafka_bootstrap_servers}")
    print()
    print("=" * 80)
    print("STREAMING JOB SUBMISSION INSTRUCTIONS")
    print("=" * 80)
    print()
    print("Streaming jobs run continuously and should be submitted manually or")
    print("deployed as long-running services. To submit this job, run:")
    print()
    print(f"  docker-compose exec -e STORAGE_FORMAT={storage_format} \\")
    print(f"    -e KAFKA_BOOTSTRAP_SERVERS={kafka_bootstrap_servers} \\")
    print(f"    -e LAKEHOUSE_PATH={lakehouse_path} \\")
    print(f"    spark-master /opt/spark/bin/spark-submit \\")
    print(f"    --master {spark_master} \\")
    print(f"    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \\")
    print(f"    {job_path}")
    print()
    print("The streaming application will run continuously in the Spark cluster.")
    print("Monitor it via Spark UI: http://localhost:8081")
    print("To stop: Kill the application via Spark UI or restart spark-master container.")
    print()
    print("=" * 80)


def verify_streaming_app_running(app_name: str, **context) -> None:
    """
    Verify that a streaming application is running in Spark cluster.
    This is a lightweight check that queries Spark REST API.
    
    Args:
        app_name: Expected application name pattern
        **context: Airflow context
    """
    import requests
    
    spark_master_ui = "http://spark-master:8080"
    
    try:
        # Query Spark REST API for running applications
        response = requests.get(f"{spark_master_ui}/api/v1/applications", timeout=5)
        if response.status_code == 200:
            apps = response.json()
            running_apps = [app for app in apps if app.get('state') == 'RUNNING']
            
            matching_apps = [app for app in running_apps if app_name.lower() in app.get('name', '').lower()]
            
            if matching_apps:
                print(f"[SUCCESS] Found {len(matching_apps)} running application(s) matching '{app_name}'")
                for app in matching_apps:
                    print(f"[INFO]   - {app.get('name')} (ID: {app.get('id')})")
            else:
                print(f"[WARN] No running applications found matching '{app_name}'")
                print(f"[INFO] Available running apps: {[app.get('name') for app in running_apps]}")
        else:
            print(f"[WARN] Could not query Spark API (status {response.status_code})")
    except Exception as e:
        print(f"[WARN] Could not verify streaming app status: {e}")
        print(f"[INFO] This is non-fatal - check Spark UI manually at http://localhost:8081")


# Task 1: Verify Kafka to Silver job is ready
task_verify_kafka_silver_ready = PythonOperator(
    task_id='verify_kafka_silver_ready',
    python_callable=verify_streaming_job_ready,
    op_kwargs={'job_script': 'stream_kafka_to_silver.py'},
    dag=dag,
)

# Task 2: Verify Kafka to Silver app is running (optional check)
task_verify_kafka_silver_running = PythonOperator(
    task_id='verify_kafka_silver_running',
    python_callable=verify_streaming_app_running,
    op_kwargs={'app_name': 'Stream_Kafka_to_Silver'},
    dag=dag,
)

# Task 3: Verify Trending to Gold job is ready
task_verify_trending_gold_ready = PythonOperator(
    task_id='verify_trending_gold_ready',
    python_callable=verify_streaming_job_ready,
    op_kwargs={'job_script': 'stream_trending_to_gold.py'},
    dag=dag,
)

# Task 4: Verify Trending to Gold app is running (optional check)
task_verify_trending_gold_running = PythonOperator(
    task_id='verify_trending_gold_running',
    python_callable=verify_streaming_app_running,
    op_kwargs={'app_name': 'Stream_Trending_to_Gold'},
    dag=dag,
)

# Define task dependencies
task_verify_kafka_silver_ready >> task_verify_kafka_silver_running >> task_verify_trending_gold_ready >> task_verify_trending_gold_running

