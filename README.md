# Système de Recommandation de Films - Écosystème Big Data

Ce projet implémente un système de recommandation de films utilisant un écosystème Big Data complet avec Docker.

## Architecture

Le système comprend les composants suivants :

- **Kafka** : Streaming de données en temps réel
- **Spark** : Traitement distribué (Master + 2 Workers)
- **Airflow** : Orchestration de workflows (Webserver + Scheduler + Worker Celery)
- **PostgreSQL** : Base de données métadonnées Airflow + MLflow
- **Redis** : Broker Celery + Cache API
- **MLflow** : Tracking des expériences ML
- **Prometheus + Grafana** : Monitoring et observabilité
- **Kafka UI** : Interface de gestion Kafka
- **FastAPI** : API de service pour les recommandations
- **Lakehouse** : Stockage Delta/Parquet

## Prérequis

- Docker Desktop (Windows/Mac) ou Docker Engine + Docker Compose (Linux)
- Au moins 8GB de RAM disponible
- 20GB d'espace disque libre

## Installation et Démarrage

### 1. Cloner le projet

```bash
git clone <repository-url>
cd Films-recommandation-system
```

### 2. Démarrer le système

**Option A : Utiliser le script d'initialisation (Recommandé)**

**Sur Windows (PowerShell) :**
```powershell
.\init.ps1
```

**Sur Linux/Mac :**
```bash
chmod +x init.sh
./init.sh
```

**Option B : Démarrage manuel**

```bash
# Démarrer PostgreSQL en premier
docker-compose up -d postgres

# Attendre que PostgreSQL soit prêt (environ 10 secondes)
# Puis créer la base de données MLflow
docker-compose exec postgres psql -U airflow -c "CREATE DATABASE mlflow;"

# Démarrer tous les services
docker-compose up -d
```

### 3. Vérifier l'état des services

```bash
docker-compose ps
```

Les services `airflow-init` et `mlflow-init` s'exécutent une seule fois pour initialiser les bases de données.

## Accès aux Services

Une fois tous les services démarrés, vous pouvez accéder à :

| Service | URL | Credentials |
|---------|-----|-------------|
| **Kafka UI** | http://localhost:8080 | - |
| **Spark Master UI** | http://localhost:8081 | - |
| **Airflow** | http://localhost:8082 | admin / admin |
| **MLflow** | http://localhost:5000 | - |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **FastAPI** | http://localhost:8000 | - |
| **FastAPI Docs** | http://localhost:8000/docs | - |

## Structure du Projet

```
.
├── docker-compose.yml          # Configuration Docker Compose
├── api/                        # Application FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── .env.example
├── airflow/                    # Configuration Airflow
│   ├── dags/                   # Vos DAGs Airflow
│   ├── logs/                   # Logs Airflow
│   ├── plugins/                # Plugins Airflow
│   └── config/                 # Configuration Airflow
├── spark/                      # Configuration Spark
│   └── config/
│       ├── spark-defaults.conf
│       └── log4j2.properties
├── prometheus/                 # Configuration Prometheus
│   ├── prometheus.yml
│   └── alerts.yml
├── grafana/                    # Configuration Grafana
│   ├── provisioning/
│   └── dashboards/
└── lakehouse/                  # Stockage des données (Delta/Parquet)
    └── bronze/                 # Bronze layer (raw data)
        └── movielens/          # MovieLens dataset
├── docs/                       # Documentation
│   ├── 01_data_contracts.md   # Data contracts and schemas
│   └── 02_step2_bootstrap_bronze.md  # Step 2 bootstrap guide
├── schemas/                    # Schema definitions
│   ├── events/                 # Kafka event JSON schemas
│   └── lakehouse/              # Lakehouse table YAML schemas
└── Makefile                    # Convenience commands
```

## Step 1: Data Contracts

The data contracts define the schemas and validation rules for the entire data pipeline.

### Documentation

- **Data Contracts**: `docs/01_data_contracts.md` - Complete data contracts including:
  - Use cases (UC1: Top-K recommendations, UC2: Trending Now, UC3: Hybrid reranking)
  - Kafka event schemas (view, click, rating events)
  - Lakehouse table schemas (Bronze, Silver, Gold layers)
  - Data quality rules and failure handling

### Schemas

- **Kafka Event Schemas**: `schemas/events/`
  - `view_event.schema.json`
  - `click_event.schema.json`
  - `rating_event.schema.json`

- **Lakehouse Table Schemas**: `schemas/lakehouse/`
  - `bronze_tables.yml`
  - `silver_tables.yml`
  - `gold_tables.yml`

### View Documentation

```bash
# View data contracts
cat docs/01_data_contracts.md

# Or use make
make docs
```

## Step 2: Bootstrap MovieLens 25M to Bronze

Download and extract the MovieLens 25M dataset to the Bronze layer.

### Prerequisites

- Internet connection (to download ~250 MB dataset)
- ~2 GB free disk space
- Python 3.6+ (for validation script)

### Bootstrap Dataset

**All Platforms (Python):**
```bash
# Using Makefile
make bootstrap_bronze

# Or directly
python scripts/bootstrap_bronze_movielens_25m.py

# With force flag (re-download)
python scripts/bootstrap_bronze_movielens_25m.py --force
```

**Alternative (Linux/Mac - Bash):**
```bash
./scripts/bootstrap_bronze_movielens_25m.sh

# With force flag
./scripts/bootstrap_bronze_movielens_25m.sh --force
```

### Validate Bronze Data

After bootstrap, validate that all files are present:

```bash
# Using Makefile
make validate_bronze

# Or directly
python scripts/validate_bronze_presence.py
```

### Expected Structure

After bootstrap, the Bronze layer will have:

```
lakehouse/
└── bronze/
    └── movielens/
        └── ml-25m/
            ├── _manifest.json      # Dataset metadata
            ├── ratings.csv         # ~25M ratings
            ├── movies.csv          # ~62K movies
            ├── tags.csv            # ~1M tags
            ├── links.csv           # Movie links
            ├── genome-scores.csv   # (optional)
            └── genome-tags.csv     # (optional)
```

### Container Access

The Bronze data is accessible from Docker containers at `/lakehouse/bronze/`:

```bash
# Verify from Spark container
docker-compose exec spark-master ls -lh /lakehouse/bronze/movielens/ml-25m/

# Verify from Airflow container
docker-compose exec airflow-worker ls -lh /lakehouse/bronze/movielens/ml-25m/
```

### Next Steps

After Step 2 completion:
1. ✅ Data contracts defined (Step 1)
2. ✅ Bronze layer bootstrapped (Step 2)
3. ✅ **Step 3**: Spark ETL Bronze → Silver (implemented)
4. ✅ **Step 4**: ALS Training and Recommendations (implemented)
5. ✅ **Step 5**: Airflow Orchestration (implemented)

See `docs/03_step3_to_step5.md` for detailed information on Steps 3-5.

## Commandes Utiles

### Vérifier l'état des services

```bash
docker-compose ps
```

### Voir les logs d'un service

```bash
docker-compose logs -f <service-name>
# Exemples:
docker-compose logs -f kafka
docker-compose logs -f spark-master
docker-compose logs -f airflow-scheduler
```

### Arrêter tous les services

```bash
docker-compose down
```

### Arrêter et supprimer les volumes (⚠️ supprime les données)

```bash
docker-compose down -v
```

### Redémarrer un service spécifique

```bash
docker-compose restart <service-name>
```

### Exécuter une commande dans un conteneur

```bash
# Exemple: Accéder au shell Spark
docker-compose exec spark-master bash

# Exemple: Créer un topic Kafka
docker-compose exec kafka kafka-topics --create --topic films --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```

## Configuration

### Kafka

- **Port interne** : `kafka:29092` (pour communication entre conteneurs)
- **Port externe** : `localhost:9092` (pour accès depuis l'hôte)

### Spark

- **Master URL** : `spark://spark-master:7077`
- Les workers sont configurés avec 2GB de mémoire et 2 cores chacun
- Le lakehouse est monté dans `/lakehouse` dans tous les conteneurs Spark

### Airflow

- **Executor** : CeleryExecutor
- **Broker** : Redis
- **Base de données** : PostgreSQL
- Les DAGs doivent être placés dans `airflow/dags/`

### MLflow

- **Backend Store** : PostgreSQL (base `mlflow`)
- **Artifact Store** : Volume Docker `mlflow-artifacts`

### FastAPI

- Les variables d'environnement sont définies dans `docker-compose.yml`
- Vous pouvez créer un fichier `.env` dans `api/` pour la configuration locale

## Développement

### Ajouter un DAG Airflow

1. Créez un fichier Python dans `airflow/dags/`
2. Le DAG sera automatiquement détecté par Airflow

### Développer l'API FastAPI

1. Modifiez les fichiers dans `api/`
2. Redémarrez le service : `docker-compose restart fastapi`
3. Ou montez le volume en développement pour le rechargement automatique

### Travailler avec Spark

```bash
# Soumettre un job Spark
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --class your.main.Class \
  your-app.jar
```

## Monitoring

### Prometheus

- Scrape les métriques de tous les services
- Configuration dans `prometheus/prometheus.yml`

### Grafana

- Dashboards pré-configurés dans `grafana/dashboards/`
- Datasource Prometheus configuré automatiquement

## Test de Connectivité

Pour vérifier que tous les services peuvent communiquer entre eux :

```bash
# Depuis le conteneur FastAPI
docker-compose exec fastapi python test-connections.py

# Ou depuis l'hôte (si les dépendances sont installées)
python test-connections.py
```

## Dépannage

### Service ne démarre pas

1. Vérifiez les logs : `docker-compose logs <service-name>`
2. Vérifiez les dépendances dans `docker-compose.yml`
3. Assurez-vous que les ports ne sont pas déjà utilisés

### Airflow ne se connecte pas à PostgreSQL

1. Vérifiez que PostgreSQL est démarré : `docker-compose ps postgres`
2. Vérifiez les logs : `docker-compose logs postgres`
3. Vérifiez les variables d'environnement dans `docker-compose.yml`
4. Réinitialisez la base de données : `docker-compose up airflow-init`

### MLflow ne se connecte pas à PostgreSQL

1. Vérifiez que la base de données MLflow existe :
   ```bash
   docker-compose exec postgres psql -U airflow -c "\l" | grep mlflow
   ```
2. Si elle n'existe pas, créez-la :
   ```bash
   docker-compose exec postgres psql -U airflow -c "CREATE DATABASE mlflow;"
   ```

### Problèmes de mémoire

Si vous rencontrez des problèmes de mémoire :
- Réduisez le nombre de workers Spark dans `docker-compose.yml`
- Réduisez la mémoire allouée aux workers : `SPARK_WORKER_MEMORY=1g`
- Arrêtez les services non essentiels temporairement

### Kafka ne démarre pas

1. Vérifiez que Zookeeper est démarré : `docker-compose ps zookeeper`
2. Vérifiez les logs : `docker-compose logs kafka`
3. Assurez-vous que les volumes Kafka ne sont pas corrompus (supprimez-les si nécessaire)

## Exemples et Scripts

### Scripts Utilitaires

- **`scripts/create-kafka-topics.sh/.ps1`** : Créer les topics Kafka nécessaires
- **`scripts/check-services.sh/.ps1`** : Vérifier l'état de tous les services
- **`test-connections.py`** : Tester la connectivité entre services

### Exemples de Code

Consultez le dossier `examples/` pour des exemples complets :

- **`kafka_producer_example.py`** : Envoyer des données vers Kafka
- **`kafka_consumer_example.py`** : Lire des données depuis Kafka
- **`spark_kafka_example.py`** : Traitement Spark avec Kafka streaming
- **`mlflow_example.py`** : Tracking d'expériences ML avec MLflow
- **`fastapi_kafka_integration.py`** : Intégration FastAPI avec Kafka

Voir [examples/README.md](examples/README.md) pour plus de détails.

## Prochaines Étapes

1. Créer vos DAGs Airflow pour l'orchestration
2. Implémenter la logique de recommandation dans Spark
3. Configurer les pipelines Kafka pour le streaming
4. Développer l'API FastAPI avec la logique métier
5. Créer des dashboards Grafana personnalisés
6. Configurer MLflow pour le tracking des modèles
7. Utiliser les exemples de code comme point de départ

## Support

Pour toute question ou problème, consultez les logs des services ou la documentation officielle de chaque outil.

