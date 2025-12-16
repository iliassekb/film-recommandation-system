# Exemples de Code

Ce dossier contient des exemples de code pour utiliser les différents composants du système de recommandation de films.

## 📚 Exemples Disponibles

### 1. Kafka

#### `kafka_producer_example.py`
Exemple de producteur Kafka pour envoyer des données de ratings et événements.

**Utilisation:**
```bash
# Depuis l'hôte
python examples/kafka_producer_example.py

# Depuis un conteneur
docker-compose exec fastapi python /app/examples/kafka_producer_example.py
```

#### `kafka_consumer_example.py`
Exemple de consommateur Kafka pour lire des données depuis les topics.

**Utilisation:**
```bash
# Consommer des ratings
python examples/kafka_consumer_example.py ratings

# Consommer des événements
python examples/kafka_consumer_example.py events

# Mode batch
python examples/kafka_consumer_example.py batch

# Mode streaming (illimité)
python examples/kafka_consumer_example.py stream
```

### 2. Spark

#### `spark_kafka_example.py`
Exemple d'utilisation de Spark avec Kafka pour le streaming de données.

**Fonctionnalités:**
- Lecture depuis Kafka
- Traitement en streaming
- Écriture dans le lakehouse (Delta format)
- Agrégations par fenêtre temporelle

**Utilisation:**
```bash
# Soumettre le job Spark
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,io.delta:delta-spark_2.12:3.0.0 \
  /lakehouse/examples/spark_kafka_example.py
```

### 3. MLflow

#### `mlflow_example.py`
Exemple d'utilisation de MLflow pour tracker les expériences de recommandation.

**Fonctionnalités:**
- Entraînement de modèles ALS (Alternating Least Squares)
- Tracking des hyperparamètres et métriques
- Enregistrement des modèles
- Comparaison de différentes configurations

**Utilisation:**
```bash
# Depuis un conteneur avec Spark
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-mllib_2.12:3.5.0 \
  /lakehouse/examples/mlflow_example.py

# Ou depuis Python (si MLflow est installé)
python examples/mlflow_example.py
```

### 4. FastAPI

#### `fastapi_kafka_integration.py`
Exemple d'intégration FastAPI avec Kafka pour envoyer des données de manière asynchrone.

**Fonctionnalités:**
- Endpoints pour soumettre des ratings
- Endpoints pour soumettre des événements
- Intégration Kafka en arrière-plan
- Documentation automatique avec Swagger

**Utilisation:**
```bash
# Ajouter ce fichier à votre API FastAPI
# Ou lancer directement
uvicorn examples.fastapi_kafka_integration:app --host 0.0.0.0 --port 8000
```

## 🔧 Prérequis

### Pour les exemples Kafka
```bash
pip install kafka-python
```

### Pour les exemples Spark
Les dépendances sont gérées via `--packages` lors de la soumission du job.

### Pour les exemples MLflow
```bash
pip install mlflow pyspark
```

### Pour les exemples FastAPI
Les dépendances sont déjà dans `api/requirements.txt`.

## 📝 Notes

1. **Bootstrap Servers**: 
   - Depuis l'hôte: `localhost:9092`
   - Depuis un conteneur: `kafka:29092`

2. **MLflow Tracking URI**:
   - Depuis l'hôte: `http://localhost:5000`
   - Depuis un conteneur: `http://mlflow:5000`

3. **Lakehouse Path**:
   - Dans les conteneurs: `/lakehouse`
   - Sur l'hôte: `./lakehouse`

## 🚀 Workflow Complet

1. **Créer les topics Kafka**:
   ```bash
   # Windows
   .\scripts\create-kafka-topics.ps1
   
   # Linux/Mac
   chmod +x scripts/create-kafka-topics.sh
   ./scripts/create-kafka-topics.sh
   ```

2. **Envoyer des données**:
   ```bash
   python examples/kafka_producer_example.py
   ```

3. **Traiter avec Spark**:
   ```bash
   docker-compose exec spark-master spark-submit \
     --master spark://spark-master:7077 \
     /lakehouse/examples/spark_kafka_example.py
   ```

4. **Entraîner un modèle avec MLflow**:
   ```bash
   python examples/mlflow_example.py
   ```

5. **Utiliser l'API**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ratings" \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1, "film_id": 1, "rating": 4.5}'
   ```

## 📖 Documentation Complète

Consultez la documentation principale dans le [README.md](../README.md) pour plus de détails sur chaque composant.

