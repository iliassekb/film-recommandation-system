"""
DAG pour configurer la connexion Spark dans Airflow
Ce DAG crée automatiquement la connexion Spark si elle n'existe pas
"""

from airflow import DAG
from airflow.models import Connection
from airflow.operators.python import PythonOperator
from airflow.utils.db import provide_session
from datetime import datetime

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

@provide_session
def create_spark_connection(session=None):
    """Créer la connexion Spark si elle n'existe pas"""
    from sqlalchemy import and_
    
    # Vérifier si la connexion existe déjà
    existing_conn = session.query(Connection).filter(
        Connection.conn_id == 'spark_default'
    ).first()
    
    if existing_conn:
        print("✅ Connexion Spark existe déjà")
        return
    
    # Créer la nouvelle connexion
    new_conn = Connection(
        conn_id='spark_default',
        conn_type='spark',
        host='spark://spark-master',
        port=7077,
        extra='{"queue": "default"}'
    )
    
    session.add(new_conn)
    session.commit()
    print("✅ Connexion Spark créée avec succès")

with DAG(
    'setup_spark_connection',
    default_args=default_args,
    description='Configurer la connexion Spark dans Airflow',
    schedule_interval=None,  # Exécuter une seule fois
    catchup=False,
    tags=['setup', 'spark'],
) as dag:

    setup_task = PythonOperator(
        task_id='create_spark_connection',
        python_callable=create_spark_connection,
    )




