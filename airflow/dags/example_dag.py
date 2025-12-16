"""
Exemple de DAG Airflow pour le système de recommandation de films
Ce DAG montre comment orchestrer des tâches avec Spark, Kafka et MLflow
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'film_recommendation_pipeline',
    default_args=default_args,
    description='Pipeline de recommandation de films',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['films', 'recommendation', 'spark', 'mlflow'],
) as dag:

    # Tâche 1: Vérifier que Kafka est prêt
    check_kafka = BashOperator(
        task_id='check_kafka',
        bash_command='echo "Checking Kafka connection..." && nc -zv kafka 29092 || exit 1',
    )

    # Tâche 2: Traitement des données avec Spark
    process_data = SparkSubmitOperator(
        task_id='process_film_data',
        application='/opt/airflow/dags/spark_jobs/process_films.py',  # À créer
        name='film_processing',
        conn_id='spark_default',
        conf={
            'spark.master': 'spark://spark-master:7077',
            'spark.executor.memory': '2g',
            'spark.driver.memory': '1g',
        },
        java_class=None,
        packages='',
        repositories='',
        total_executor_cores=4,
        executor_cores=2,
        executor_memory='2g',
        driver_memory='1g',
        keytab='',
        principal='',
        proxy_user=None,
        num_executors=2,
        application_args=[],
        env_vars=None,
        verbose=False,
    )

    # Tâche 3: Entraînement du modèle (exemple)
    train_model = BashOperator(
        task_id='train_recommendation_model',
        bash_command='''
        echo "Training recommendation model..."
        # Ici vous pouvez appeler un script Python qui utilise MLflow
        python /opt/airflow/dags/scripts/train_model.py
        ''',
    )

    # Tâche 4: Évaluation du modèle
    evaluate_model = BashOperator(
        task_id='evaluate_model',
        bash_command='echo "Evaluating model performance..."',
    )

    # Tâche 5: Publication des recommandations
    publish_recommendations = BashOperator(
        task_id='publish_recommendations',
        bash_command='echo "Publishing recommendations to Kafka..."',
    )

    # Définir l'ordre d'exécution
    check_kafka >> process_data >> train_model >> evaluate_model >> publish_recommendations

