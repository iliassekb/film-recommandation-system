# Guide des Connexions entre Services

Ce document décrit comment les différents services communiquent entre eux dans l'écosystème Big Data.

## Réseau Docker

Tous les services sont connectés au réseau `bigdata-network`, ce qui leur permet de communiquer entre eux en utilisant leurs noms d'hôte.

## Connexions par Service

### Kafka
- **Zookeeper** : `zookeeper:2181`
- **Bootstrap Servers (interne)** : `kafka:29092`
- **Bootstrap Servers (externe)** : `localhost:9092`
- **Kafka UI** : Se connecte à `kafka:29092` et `zookeeper:2181`

### Spark
- **Master URL** : `spark://spark-master:7077`
- **Master UI** : `http://spark-master:8080` (externe: `http://localhost:8081`)
- **Workers** : Se connectent au master via `spark-master:7077`
- **Lakehouse** : Monté dans `/lakehouse` (partagé avec tous les services)

### Airflow
- **PostgreSQL (Metadata DB)** : `postgres:5432`
  - User: `airflow`
  - Password: `airflow`
  - Database: `airflow`
- **Redis (Celery Broker)** : `redis:6379/0`
- **Spark** : `spark://spark-master:7077`
- **Kafka** : `kafka:29092`
- **Lakehouse** : `/lakehouse`

### PostgreSQL
- **Port** : `5432`
- **User** : `airflow`
- **Password** : `airflow`
- **Databases** :
  - `airflow` : Métadonnées Airflow
  - `mlflow` : Métadonnées MLflow

### Redis
- **Host** : `redis`
- **Port** : `6379`
- **Database 0** : Broker Celery pour Airflow
- **Database 1+** : Cache pour FastAPI (optionnel)

### MLflow
- **PostgreSQL (Backend Store)** : `postgresql://airflow:airflow@postgres:5432/mlflow`
- **Artifact Store** : `/mlflow/artifacts` (volume Docker)
- **Tracking URI** : `http://mlflow:5000` (interne) ou `http://localhost:5000` (externe)

### FastAPI
- **PostgreSQL** : `postgres:5432`
  - User: `airflow`
  - Password: `airflow`
  - Database: `airflow`
- **Redis** : `redis:6379`
- **Kafka** : `kafka:29092`
- **MLflow** : `http://mlflow:5000`
- **Lakehouse** : `/lakehouse`

### Prometheus
- **Port** : `9090`
- **Scrape Targets** :
  - `localhost:9090` (Prometheus lui-même)
  - `kafka:9092` (Kafka)
  - `spark-master:8080` (Spark Master)
  - `airflow-webserver:8080` (Airflow)
  - `redis:6379` (Redis)
  - `postgres:5432` (PostgreSQL)
  - `mlflow:5000` (MLflow)
  - `fastapi:8000` (FastAPI)

### Grafana
- **Prometheus Datasource** : `http://prometheus:9090`
- **Port** : `3000`
- **Credentials** : `admin/admin`

## Variables d'Environnement

### FastAPI
```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
REDIS_HOST=redis
REDIS_PORT=6379
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
MLFLOW_TRACKING_URI=http://mlflow:5000
LAKEHOUSE_PATH=/lakehouse
```

### Airflow
```bash
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
AIRFLOW__CELERY__BROKER_URL=redis://redis:6379/0
AIRFLOW__CELERY__RESULT_BACKEND=db+postgresql://airflow:airflow@postgres/airflow
```

### MLflow
```bash
MLFLOW_BACKEND_STORE_URI=postgresql://airflow:airflow@postgres:5432/mlflow
MLFLOW_DEFAULT_ARTIFACT_ROOT=/mlflow/artifacts
```

## Exemples de Connexion

### Depuis Python (dans un conteneur)

```python
# Kafka
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='kafka:29092')

# PostgreSQL
import psycopg2
conn = psycopg2.connect(
    host='postgres',
    port=5432,
    user='airflow',
    password='airflow',
    database='airflow'
)

# Redis
import redis
r = redis.Redis(host='redis', port=6379, db=0)

# MLflow
import mlflow
mlflow.set_tracking_uri('http://mlflow:5000')
```

### Depuis Spark (dans un conteneur Spark)

```python
# Connexion à Kafka depuis Spark
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "films") \
    .load()

# Lecture depuis le lakehouse
df = spark.read.format("delta").load("/lakehouse/films")
```

### Depuis Airflow DAG

```python
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

spark_task = SparkSubmitOperator(
    task_id='spark_job',
    application='/path/to/app.py',
    conn_id='spark_default',  # spark://spark-master:7077
    conf={'spark.master': 'spark://spark-master:7077'}
)
```

## Test de Connectivité

Vous pouvez tester les connexions depuis n'importe quel conteneur :

```bash
# Tester PostgreSQL
docker-compose exec fastapi psql -h postgres -U airflow -d airflow -c "SELECT 1;"

# Tester Redis
docker-compose exec fastapi redis-cli -h redis ping

# Tester Kafka
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Tester MLflow
docker-compose exec fastapi curl http://mlflow:5000/health
```

