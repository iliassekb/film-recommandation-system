# Générateur d'Événements de Streaming

Script Python pour générer des événements de streaming (views, clicks, ratings) et les envoyer dans Kafka.

## Installation

Le script utilise `kafka-python`. Si vous l'exécutez localement :

```bash
pip install kafka-python
```

Si vous l'exécutez dans un conteneur Docker, la dépendance est déjà installée.

## Utilisation

### Mode Batch (par défaut)

Génère un nombre fixe d'événements et s'arrête :

```bash
# Depuis votre machine (Windows)
python tools/generate_streaming_events.py --mode batch --num-events 100

# Depuis un conteneur Docker
docker-compose exec -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  kafka-topic-init python3 -c "
    pip install --no-cache-dir kafka-python==2.0.2 && \
    python -c \"
import sys
sys.path.insert(0, '/app/tools')
from generate_streaming_events import StreamingEventGenerator
gen = StreamingEventGenerator('kafka:29092')
gen.generate_and_send_batch(100)
gen.close()
\"
  "
```

### Mode Stream Continu

Génère des événements en continu :

```bash
# 10 événements par seconde, durée infinie (Ctrl+C pour arrêter)
python tools/generate_streaming_events.py --mode stream --events-per-second 10

# 5 événements par seconde pendant 60 secondes
python tools/generate_streaming_events.py --mode stream --events-per-second 5 --duration 60
```

### Options

- `--bootstrap-servers`: Adresse Kafka (default: localhost:9092)
- `--mode`: `batch` ou `stream` (default: batch)
- `--num-events`: Nombre d'événements pour batch (default: 100)
- `--events-per-second`: Événements/seconde pour stream (default: 10.0)
- `--duration`: Durée en secondes pour stream (default: infini)

## Exemple d'Utilisation Complète

### 1. Démarrer les services

```bash
docker-compose up -d kafka zookeeper kafka-ui
```

### 2. Vérifier que les topics existent

```bash
# Vérifier dans Kafka UI: http://localhost:8080
# Ou via commande:
docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:29092
```

### 3. Lancer les jobs Spark Streaming (dans des terminaux séparés)

**Terminal 1 - Kafka → Silver:**
```bash
docker-compose exec -e STORAGE_FORMAT=parquet \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  -e LAKEHOUSE_PATH=/data \
  spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
  /opt/spark/jobs/stream_kafka_to_silver.py
```

**Terminal 2 - Silver → Gold (Trending):**
```bash
docker-compose exec -e STORAGE_FORMAT=parquet \
  -e LAKEHOUSE_PATH=/data \
  spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
  /opt/spark/jobs/stream_trending_to_gold.py
```

### 4. Générer des événements

**Option A - Depuis votre machine (si Python et kafka-python installés):**
```bash
python tools/generate_streaming_events.py \
  --bootstrap-servers localhost:9092 \
  --mode stream \
  --events-per-second 5
```

**Option B - Depuis un conteneur Python:**
```bash
docker run --rm -it \
  --network films-recommandation-system_bigdata-network \
  -v ${PWD}/tools:/app/tools \
  python:3.11-slim bash -c "
    pip install --no-cache-dir kafka-python==2.0.2 && \
    python /app/tools/generate_streaming_events.py \
      --bootstrap-servers kafka:29092 \
      --mode stream \
      --events-per-second 5
  "
```

### 5. Vérifier les résultats

**Dans Kafka UI:** http://localhost:8080
- Vérifiez que les messages arrivent dans les topics

**Dans le lakehouse:**
```bash
# Vérifier Silver
docker-compose exec spark-master ls -R /data/silver

# Vérifier Gold
docker-compose exec spark-master ls -R /data/gold

# Lire les données
docker-compose exec spark-master /opt/spark/bin/spark-shell \
  --master spark://spark-master:7077 \
  -e 'spark.read.parquet("/data/silver/events_views").show(10)'
```

## Distribution des Événements

Par défaut, le script génère :
- **60%** d'événements `views`
- **30%** d'événements `clicks`
- **10%** d'événements `ratings`

Cette distribution peut être modifiée dans le code si nécessaire.

## Statistiques

Le script affiche des statistiques en temps réel :
- Nombre de views envoyées
- Nombre de clicks envoyés
- Nombre de ratings envoyés
- Nombre d'erreurs (si applicable)

## Exemples d'Événements Générés

### View Event
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "view",
  "event_ts": "2025-12-17T17:30:00.000Z",
  "user_id": 123,
  "movie_id": 456,
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "device_type": "mobile"
}
```

### Click Event
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440002",
  "event_type": "click",
  "event_ts": "2025-12-17T17:30:05.000Z",
  "user_id": 123,
  "movie_id": 456,
  "click_type": "trailer",
  "session_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

### Rating Event
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440003",
  "event_type": "rating",
  "event_ts": "2025-12-17T17:30:10.000Z",
  "user_id": 123,
  "movie_id": 456,
  "rating": 4.5,
  "review_text": "Great movie!"
}
```

## Dépannage

### Erreur de connexion Kafka

Vérifiez que Kafka est démarré :
```bash
docker-compose ps kafka
```

Vérifiez l'adresse bootstrap :
```bash
# Depuis un conteneur
docker-compose exec kafka-topic-init ping kafka

# Depuis votre machine
ping localhost
```

### Topics non trouvés

Les topics sont créés automatiquement, mais vous pouvez les créer manuellement :
```bash
docker-compose exec kafka kafka-topics --create \
  --bootstrap-server kafka:29092 \
  --topic events_views \
  --partitions 3 \
  --replication-factor 1
```

### Messages non reçus

1. Vérifiez les logs Spark Streaming
2. Vérifiez que les jobs Spark sont actifs
3. Vérifiez les checkpoints : `/data/_checkpoints/`
4. Vérifiez les dead-letters : `/data/silver/_deadletter/`




