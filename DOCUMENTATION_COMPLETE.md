# Documentation Complète - Système de Recommandation de Films

Ce document consolide toute la documentation du projet en un seul fichier de référence.

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Installation et Démarrage](#installation-et-démarrage)
4. [Structure du Projet](#structure-du-projet)
5. [Connexions entre Services](#connexions-entre-services)
6. [Step 1: Data Contracts](#step-1-data-contracts)
7. [Step 2: Bootstrap Bronze Layer](#step-2-bootstrap-bronze-layer)
8. [Scripts Utilitaires](#scripts-utilitaires)
9. [Exemples de Code](#exemples-de-code)
10. [Configuration](#configuration)
11. [Monitoring](#monitoring)
12. [Dépannage](#dépannage)
13. [Prochaines Étapes](#prochaines-étapes)

---

## Vue d'ensemble

Ce projet implémente un système de recommandation de films utilisant un écosystème Big Data complet avec Docker. Le système traite des données de films, génère des recommandations personnalisées et fournit une API pour servir les résultats.

### Objectifs

- Traitement distribué de grandes quantités de données (MovieLens 25M)
- Streaming de données en temps réel via Kafka
- Génération de recommandations personnalisées (ALS)
- Détection de tendances en temps réel
- API REST pour servir les recommandations
- Monitoring et observabilité complets

---

## Architecture

### Composants Principaux

| Service | Port | Description |
|---------|------|-------------|
| **Kafka** | 9092 | Streaming de données en temps réel |
| **Kafka UI** | 8080 | Interface de gestion Kafka |
| **Zookeeper** | 2181 | Coordination Kafka |
| **Spark Master** | 8081 | Orchestrateur Spark |
| **Spark Workers** | - | 2 workers pour traitement distribué |
| **Airflow** | 8082 | Orchestration de workflows (admin/admin) |
| **PostgreSQL** | 5432 | Métadonnées Airflow + MLflow |
| **Redis** | 6379 | Broker Celery + Cache API |
| **MLflow** | 5000 | Tracking des expériences ML |
| **Prometheus** | 9090 | Collecte de métriques |
| **Grafana** | 3000 | Visualisation (admin/admin) |
| **FastAPI** | 8000 | API de service |
| **FastAPI Docs** | 8000/docs | Documentation interactive |

### Architecture des Données

```
┌─────────────┐
│   Kafka     │ ──► Streaming Events (view, click, rating)
└─────────────┘
       │
       ▼
┌─────────────┐
│    Spark    │ ──► Traitement distribué
└─────────────┘
       │
       ▼
┌─────────────┐
│  Lakehouse  │ ──► Bronze → Silver → Gold
│  (Delta)    │     (Raw → Cleaned → Aggregated)
└─────────────┘
       │
       ▼
┌─────────────┐
│   FastAPI   │ ──► API REST pour recommandations
└─────────────┘
```

### Layers du Lakehouse

- **Bronze**: Données brutes (CSV, JSON) - Stockage Parquet
- **Silver**: Données nettoyées et validées - Format Delta Lake
- **Gold**: Agrégations et résultats ML - Format Delta Lake

---

## Installation et Démarrage

### Prérequis

- Docker Desktop (Windows/Mac) ou Docker Engine + Docker Compose (Linux)
- Au moins 8GB de RAM disponible
- 20GB d'espace disque libre
- Python 3.6+ (pour les scripts de validation)

### Démarrage Rapide

**Windows (PowerShell):**
```powershell
.\init.ps1
```

**Linux/Mac:**
```bash
chmod +x init.sh
./init.sh
```

Le script d'initialisation :
1. Démarre PostgreSQL
2. Crée la base de données MLflow
3. Démarre tous les services
4. Initialise Airflow

### Vérification

```bash
# Vérifier l'état des services
docker-compose ps

# Tester la connectivité
docker-compose exec fastapi python test-connections.py
```

---

## Structure du Projet

```
Films-recommandation-system/
├── docker-compose.yml              # Configuration principale
├── docker-compose.override.yml.example
│
├── README.md                        # Documentation principale
├── DOCUMENTATION_COMPLETE.md        # Ce fichier (résumé consolidé)
│
├── init.sh / init.ps1               # Scripts d'initialisation
├── test-connections.py              # Test de connectivité
├── Makefile                         # Commandes utiles
│
├── api/                             # Application FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── .env.example
│
├── airflow/                         # Configuration Airflow
│   ├── dags/                        # DAGs Airflow
│   ├── logs/                        # Logs (générés)
│   ├── plugins/                     # Plugins personnalisés
│   └── config/                      # Configuration
│
├── spark/                           # Configuration Spark
│   └── config/
│       ├── spark-defaults.conf
│       └── log4j2.properties
│
├── prometheus/                      # Configuration Prometheus
│   ├── prometheus.yml
│   └── alerts.yml
│
├── grafana/                         # Configuration Grafana
│   ├── dashboards/
│   └── provisioning/
│
├── mlflow/                          # Configuration MLflow
│   └── Dockerfile
│
├── lakehouse/                       # Stockage des données
│   └── bronze/                      # Bronze layer
│       └── movielens/
│           └── ml-25m/
│
├── schemas/                         # Définitions de schémas
│   ├── events/                      # Schémas JSON Kafka
│   └── lakehouse/                   # Schémas YAML tables
│
├── scripts/                         # Scripts utilitaires
│   ├── bootstrap_bronze_movielens_25m.py  # Bootstrap dataset
│   ├── validate_bronze_presence.py        # Validation
│   ├── create-kafka-topics.sh/.ps1
│   ├── check-services.sh/.ps1
│   ├── backup-data.sh/.ps1
│   ├── cleanup.sh/.ps1
│   ├── restart-services.ps1
│   └── README.md
│
└── examples/                        # Exemples de code
    ├── kafka_producer_example.py
    ├── kafka_consumer_example.py
    ├── spark_kafka_example.py
    ├── mlflow_example.py
    ├── fastapi_kafka_integration.py
    └── README.md
```

---

## Connexions entre Services

### Réseau Docker

Tous les services sont connectés au réseau `bigdata-network` et communiquent via leurs noms d'hôte.

### Connexions par Service

**Kafka:**
- Zookeeper: `zookeeper:2181`
- Bootstrap Servers (interne): `kafka:29092`
- Bootstrap Servers (externe): `localhost:9092`

**Spark:**
- Master URL: `spark://spark-master:7077`
- Lakehouse: `/lakehouse` (monté dans tous les conteneurs)

**Airflow:**
- PostgreSQL: `postgres:5432` (user: `airflow`, password: `airflow`, db: `airflow`)
- Redis: `redis:6379/0` (Celery broker)
- Spark: `spark://spark-master:7077`
- Kafka: `kafka:29092`

**PostgreSQL:**
- Port: `5432`
- User: `airflow`
- Password: `airflow`
- Databases: `airflow`, `mlflow`

**Redis:**
- Host: `redis`
- Port: `6379`
- Database 0: Broker Celery
- Database 1+: Cache FastAPI

**MLflow:**
- Backend Store: `postgresql://airflow:airflow@postgres:5432/mlflow`
- Artifact Store: `/mlflow/artifacts`
- Tracking URI: `http://mlflow:5000` (interne) ou `http://localhost:5000` (externe)

**FastAPI:**
- PostgreSQL: `postgres:5432`
- Redis: `redis:6379`
- Kafka: `kafka:29092`
- MLflow: `http://mlflow:5000`
- Lakehouse: `/lakehouse`

**Prometheus:**
- Scrape tous les services sur leurs ports respectifs

**Grafana:**
- Datasource: `http://prometheus:9090`

### Variables d'Environnement Clés

**FastAPI:**
```
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

**Airflow:**
```
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
AIRFLOW__CELERY__BROKER_URL=redis://redis:6379/0
AIRFLOW__CELERY__RESULT_BACKEND=db+postgresql://airflow:airflow@postgres/airflow
```

---

## Step 1: Data Contracts

### Use Cases

1. **UC1: Top-K Personalized Recommendations**
   - Génération de recommandations personnalisées avec ALS (Alternating Least Squares)
   - Traitement batch (mise à jour quotidienne/hebdomadaire)

2. **UC2: Trending Now**
   - Identification des films tendances basée sur les interactions récentes
   - Mise à jour quasi temps réel (toutes les quelques minutes)

3. **UC3: Hybrid Reranking**
   - Combinaison des recommandations ALS avec les signaux de tendance
   - Réponse API temps réel (< 100ms)

### Conventions de Nommage

- **Fichiers/Dossiers**: `snake_case`
- **Tables**: `snake_case` avec préfixe de layer (ex: `bronze_events_views_raw`)
- **Colonnes**: `snake_case`
- **Topics Kafka**: `snake_case` (ex: `events_views`, `events_clicks`, `events_ratings`)

### Schémas Kafka Events

**Événements communs (tous les types):**
- `event_id` (UUID, requis)
- `event_type` (enum: "view", "click", "rating", requis)
- `event_ts` (ISO-8601 string, requis)
- `user_id` (integer, requis)
- `movie_id` (integer, requis)

**View Event** (`events_views`):
- Champs optionnels: `session_id`, `page_url`, `device_type`

**Click Event** (`events_clicks`):
- Champs optionnels: `click_type`, `session_id`, `referrer`

**Rating Event** (`events_ratings`):
- `rating` (float 0.5-5.0, requis)
- Champs optionnels: `review_text` (max 5000 chars)

### Schémas Lakehouse

**Bronze Layer** (Données brutes):
- `bronze_movielens_ratings_raw`
- `bronze_movielens_movies_raw`
- `bronze_movielens_tags_raw`
- `bronze_events_views_raw`
- `bronze_events_clicks_raw`
- `bronze_events_ratings_raw`
- Format: Parquet
- Partition: `ingestion_date`

**Silver Layer** (Données nettoyées):
- `silver_ratings`
- `silver_movies`
- `silver_tags`
- `silver_events_views`
- `silver_events_clicks`
- `silver_events_ratings`
- Format: Delta Lake
- Partition: `event_date`

**Gold Layer** (Agrégations):
- `gold_recommendations_als`
- `gold_trending_now`
- `gold_recommendations_final`
- Format: Delta Lake
- Partition: `computed_date`

### Règles de Qualité des Données

1. **Complétude**: Champs requis non null
2. **Validité**: IDs positifs, ratings 0.5-5.0, timestamps valides
3. **Unicité**: Event IDs uniques, déduplication dans Silver
4. **Cohérence**: Références valides (movies/users existent)
5. **Fraîcheur**: Ingestion Bronze < 5 min, Silver < 1h, Gold quotidien

### Gestion des Erreurs

- Événements invalides → Dead-letter queue (`events_dlq`)
- Références manquantes → Création de placeholders
- Duplicatas → Conservation du plus récent
- Échecs qualité > 5% → Échec du job ETL

### Schémas JSON Disponibles

Les schémas JSON pour les événements Kafka sont disponibles dans :
- `schemas/events/view_event.schema.json`
- `schemas/events/click_event.schema.json`
- `schemas/events/rating_event.schema.json`

### Schémas YAML Lakehouse Disponibles

Les spécifications de schémas pour les tables lakehouse sont disponibles dans :
- `schemas/lakehouse/bronze_tables.yml`
- `schemas/lakehouse/silver_tables.yml`
- `schemas/lakehouse/gold_tables.yml`

---

## Step 2: Bootstrap Bronze Layer

### Objectif

Télécharger et extraire le dataset MovieLens 25M dans la couche Bronze.

### Dataset

- **Source**: https://files.grouplens.org/datasets/movielens/ml-25m.zip
- **Taille**: ~250 MB compressé, ~1.5 GB décompressé
- **Fichiers**: `ratings.csv` (~25M), `movies.csv` (~62K), `tags.csv` (~1M), `links.csv`

### Bootstrap

**Toutes plateformes (Python - Recommandé):**
```bash
# Avec Makefile
make bootstrap_bronze

# Ou directement
python scripts/bootstrap_bronze_movielens_25m.py

# Forcer le re-téléchargement
python scripts/bootstrap_bronze_movielens_25m.py --force
```

**Linux/Mac (Bash - Alternative):**
```bash
./scripts/bootstrap_bronze_movielens_25m.sh
```

### Validation

```bash
# Avec Makefile
make validate_bronze

# Ou directement
python scripts/validate_bronze_presence.py
```

### Structure Résultante

```
lakehouse/bronze/movielens/ml-25m/
├── _manifest.json      # Métadonnées du dataset
├── ratings.csv         # ~25M ratings
├── movies.csv          # ~62K movies
├── tags.csv            # ~1M tags
├── links.csv           # Liens externes
├── genome-scores.csv   # (optionnel)
└── genome-tags.csv     # (optionnel)
```

### Manifest File

Le fichier `_manifest.json` contient :
- `dataset_name`: "movielens"
- `dataset_version`: "ml-25m"
- `source_url`: URL de téléchargement
- `ingestion_ts`: Timestamp ISO-8601
- `ingestion_date`: Date d'ingestion
- `files`: Liste des fichiers avec tailles, row counts, checksums MD5

### Critères d'Acceptation

✅ Tous les fichiers CSV requis présents
✅ Manifest file présent et valide
✅ Validation script passe (exit code 0)
✅ Fichiers accessibles depuis conteneurs (`/lakehouse`)

### Accès depuis Conteneurs

```bash
# Vérifier depuis Spark
docker-compose exec spark-master ls -lh /lakehouse/bronze/movielens/ml-25m/

# Vérifier depuis Airflow
docker-compose exec airflow-worker ls -lh /lakehouse/bronze/movielens/ml-25m/
```

---

## Scripts Utilitaires

### Scripts Disponibles

1. **Bootstrap Dataset**
   - `bootstrap_bronze_movielens_25m.py` (Python, cross-platform)
   - `bootstrap_bronze_movielens_25m.sh` (Bash, Linux/Mac)

2. **Validation**
   - `validate_bronze_presence.py` (Python, cross-platform)

3. **Gestion Kafka**
   - `create-kafka-topics.sh/.ps1` - Créer les topics Kafka

4. **Vérification Services**
   - `check-services.sh/.ps1` - Vérifier l'état des services

5. **Maintenance**
   - `backup-data.sh/.ps1` - Sauvegarder données et configs
   - `cleanup.sh/.ps1` - Nettoyer fichiers temporaires
   - `restart-services.ps1` - Redémarrer services séquentiellement

### Makefile Commands

```bash
make bootstrap_bronze  # Bootstrap MovieLens dataset
make validate_bronze    # Valider Bronze layer
make docs               # Ouvrir documentation
make clean              # Nettoyer fichiers temporaires
```

Voir `scripts/README.md` pour la documentation complète des scripts.

---

## Exemples de Code

### Kafka

**Producteur** (`kafka_producer_example.py`):
```python
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='localhost:9092')
producer.send('events_ratings', value=json.dumps(event).encode())
```

**Consommateur** (`kafka_consumer_example.py`):
```python
from kafka import KafkaConsumer
consumer = KafkaConsumer('events_ratings', bootstrap_servers='localhost:9092')
for message in consumer:
    process_event(message.value)
```

### Spark + Kafka Streaming

**Exemple** (`spark_kafka_example.py`):
- Lecture depuis Kafka
- Traitement streaming
- Écriture Delta Lake
- Agrégations par fenêtre temporelle

### MLflow

**Exemple** (`mlflow_example.py`):
- Entraînement modèles ALS
- Tracking hyperparamètres et métriques
- Enregistrement modèles
- Comparaison configurations

### FastAPI + Kafka

**Exemple** (`fastapi_kafka_integration.py`):
- Endpoints pour ratings et événements
- Intégration Kafka asynchrone
- Documentation Swagger automatique

Voir `examples/README.md` pour la documentation complète des exemples.

---

## Configuration

### Kafka

- Port interne: `kafka:29092`
- Port externe: `localhost:9092`
- Topics: `events_views`, `events_clicks`, `events_ratings`

### Spark

- Master URL: `spark://spark-master:7077`
- Workers: 2 workers (2GB RAM, 2 cores chacun)
- Lakehouse: `/lakehouse` dans tous les conteneurs
- Format: Delta Lake configuré

### Airflow

- Executor: CeleryExecutor
- Broker: Redis (`redis:6379/0`)
- Database: PostgreSQL (`postgres:5432`)
- DAGs: `airflow/dags/`
- Credentials: admin/admin

### MLflow

- Backend Store: PostgreSQL (`mlflow` database)
- Artifact Store: Volume Docker `mlflow-artifacts`
- Tracking URI: `http://mlflow:5000`

### FastAPI

- Variables d'environnement dans `docker-compose.yml`
- Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## Monitoring

### Prometheus

- Port: `9090`
- Scrape tous les services automatiquement
- Configuration: `prometheus/prometheus.yml`
- Alertes: `prometheus/alerts.yml`

### Grafana

- Port: `3000`
- Credentials: admin/admin
- Datasource: Prometheus (auto-configuré)
- Dashboards: `grafana/dashboards/`

### Kafka UI

- Port: `8080`
- Interface web pour gérer Kafka
- Visualisation des topics et messages

---

## Dépannage

### Service ne démarre pas

1. Vérifier les logs: `docker-compose logs <service-name>`
2. Vérifier les dépendances dans `docker-compose.yml`
3. Vérifier que les ports ne sont pas utilisés

### Airflow ne se connecte pas à PostgreSQL

1. Vérifier que PostgreSQL est démarré: `docker-compose ps postgres`
2. Vérifier les logs: `docker-compose logs postgres`
3. Réinitialiser: `docker-compose up airflow-init`

### MLflow ne se connecte pas à PostgreSQL

1. Vérifier que la DB existe:
   ```bash
   docker-compose exec postgres psql -U airflow -c "\l" | grep mlflow
   ```
2. Créer si nécessaire:
   ```bash
   docker-compose exec postgres psql -U airflow -c "CREATE DATABASE mlflow;"
   ```

### Problèmes de mémoire

- Réduire nombre de workers Spark
- Réduire mémoire workers: `SPARK_WORKER_MEMORY=1g`
- Arrêter services non essentiels

### Kafka ne démarre pas

1. Vérifier Zookeeper: `docker-compose ps zookeeper`
2. Vérifier les logs: `docker-compose logs kafka zookeeper`
3. Supprimer volumes corrompus si nécessaire

---

## Commandes Utiles

### Gestion Docker

```bash
# Vérifier l'état
docker-compose ps

# Voir les logs
docker-compose logs -f <service-name>

# Redémarrer un service
docker-compose restart <service-name>

# Arrêter tout
docker-compose down

# Arrêter et supprimer volumes (⚠️ supprime données)
docker-compose down -v
```

### Exécuter dans un conteneur

```bash
# Shell Spark
docker-compose exec spark-master bash

# Créer topic Kafka
docker-compose exec kafka kafka-topics --create \
  --topic events_views \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

# Tester connectivité
docker-compose exec fastapi python test-connections.py
```

### Spark Jobs

```bash
# Soumettre job Spark
docker-compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  /path/to/your/script.py
```

---

## Prochaines Étapes

### Développement

1. ✅ **Step 1**: Data Contracts définis
2. ✅ **Step 2**: Bootstrap Bronze layer complété
3. ⏭️ **Step 3**: Implémenter ETL Bronze → Silver (Spark)
4. ⏭️ **Step 4**: Ingestion streaming Kafka → Bronze/Silver
5. ⏭️ **Step 5**: Pipelines ML (ALS, Trending, Hybrid)

### Actions Recommandées

1. **Créer DAGs Airflow** personnalisés dans `airflow/dags/`
2. **Développer logique recommandation** dans Spark
3. **Configurer pipelines Kafka** pour streaming
4. **Développer API FastAPI** avec endpoints métier
5. **Créer dashboards Grafana** personnalisés
6. **Configurer MLflow** pour tracking modèles
7. **Utiliser exemples** dans `examples/` comme point de départ

### Workflow de Développement

1. Démarrer système: `.\init.ps1` ou `./init.sh`
2. Bootstrap données: `make bootstrap_bronze`
3. Créer topics Kafka: `.\scripts\create-kafka-topics.ps1`
4. Explorer exemples: `examples/`
5. Développer DAGs: `airflow/dags/`
6. Tester API: `http://localhost:8000/docs`

---

## Support

Pour toute question ou problème:
1. Consulter les logs: `docker-compose logs <service-name>`
2. Vérifier la documentation officielle de chaque outil
3. Consulter les sections Dépannage ci-dessus
4. Vérifier que Docker a assez de ressources

---

**Dernière mise à jour**: Décembre 2025
**Version**: 1.0
**Statut**: Step 1 & Step 2 complétés ✅

