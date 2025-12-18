# Guide de Test du Streaming Pipeline

Guide rapide pour tester le pipeline de streaming complet.

## Vue d'Ensemble

```
Générateur d'Événements → Kafka → Spark Streaming → Silver → Spark Streaming → Gold
```

## Étapes de Test

### 1. Démarrer les Services

```bash
# Démarrer Kafka et Zookeeper
docker-compose up -d zookeeper kafka kafka-ui

# Démarrer Spark
docker-compose up -d spark-master spark-worker-1 spark-worker-2

# Attendre que tout soit prêt (10-15 secondes)
```

### 2. Vérifier les Topics Kafka

```bash
# Vérifier que les topics existent
docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:29092

# Devrait afficher:
# events_views
# events_clicks
# events_ratings
```

Ou vérifier dans Kafka UI: http://localhost:8080

### 3. Installer les JARs Kafka (IMPORTANT - Une seule fois)

**⚠️ IMPORTANT**: Les JARs Kafka doivent être installés dans `/opt/spark/jars` sur tous les conteneurs Spark (master et workers) pour que les executors puissent les utiliser.

**Sur Linux/Mac:**
```bash
chmod +x scripts/install_kafka_jars.sh
./scripts/install_kafka_jars.sh
```

**Sur Windows (PowerShell):**
```powershell
.\scripts\install_kafka_jars.ps1
```

**Ou manuellement:**
```bash
# Télécharger les JARs sur le master
docker-compose exec spark-master bash -c 'mkdir -p /tmp/spark-jars && cd /tmp/spark-jars && curl -L -o kafka-clients.jar https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar && curl -L -o spark-sql-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.4.0/spark-sql-kafka-0-10_2.12-3.4.0.jar && curl -L -o spark-token-provider-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.4.0/spark-token-provider-kafka-0-10_2.12-3.4.0.jar'

# Copier dans /opt/spark/jars sur tous les conteneurs (avec sudo pour les permissions)
for container in spark-master spark-worker-1 spark-worker-2; do
  docker-compose exec $container bash -c 'sudo mkdir -p /opt/spark/jars && sudo cp /tmp/spark-jars/*.jar /opt/spark/jars/ && sudo chmod 644 /opt/spark/jars/*kafka*.jar'
done
```

### 4. Lancer le Job Kafka → Silver

**Dans un terminal séparé**, lancez :

```bash
docker-compose exec spark-master bash -c 'export STORAGE_FORMAT=parquet && export KAFKA_BOOTSTRAP_SERVERS=kafka:29092 && export LAKEHOUSE_PATH=/data && /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/stream_kafka_to_silver.py'
```

**Note**: Plus besoin de `--jars` car les JARs sont maintenant dans `/opt/spark/jars` sur tous les conteneurs.

**Laissez ce terminal ouvert** - le job doit rester actif.

### 5. Lancer le Job Silver → Gold (Trending)

**Dans un autre terminal**, lancez :

```bash
docker-compose exec spark-master bash -c 'export STORAGE_FORMAT=parquet && export LAKEHOUSE_PATH=/data && /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/stream_trending_to_gold.py'
```

**Laissez ce terminal ouvert** aussi.

### 6. Générer des Événements

**Option A - Mode Batch (100 événements) - Utilise docker-compose (Recommandé):**

```bash
docker-compose run --rm \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  kafka-topic-init sh -c "
    pip install --no-cache-dir kafka-python==2.0.2 && \
    python3 /app/tools/run_event_generator.py \
      --mode batch \
      --num-events 100
  "
```

**Option B - Mode Stream Continu (5ms entre événements, Ctrl+C pour arrêter) - Utilise docker-compose:**

```bash
docker-compose run --rm \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  kafka-topic-init sh -c "
    pip install --no-cache-dir kafka-python==2.0.2 && \
    python3 /app/tools/run_event_generator.py \
      --mode stream \
      --interval-ms 5
  "
```

**Note**: Le générateur affiche chaque événement généré et ne s'arrête que sur Ctrl+C. Les micro-batches Spark traitent les données toutes les 5 secondes.

**Option C - Depuis votre machine (si Python installé):**

```bash
pip install kafka-python
python tools/generate_streaming_events.py \
  --bootstrap-servers localhost:9092 \
  --mode stream \
  --events-per-second 5
```

### 7. Vérifier les Résultats

**Dans Kafka UI:** http://localhost:8080
- Vérifiez que les messages arrivent dans les topics

**Dans Spark UI:** http://localhost:8081
- Vérifiez que les applications streaming sont actives
- Vérifiez les métriques de traitement

**Dans le Lakehouse:**

```bash
# Vérifier les fichiers Silver créés
docker-compose exec spark-master ls -R /data/silver/

# Vérifier les fichiers Gold créés
docker-compose exec spark-master ls -R /data/gold/

# Lire les données Silver
docker-compose exec spark-master /opt/spark/bin/spark-shell \
  --master spark://spark-master:7077 \
  -e 'spark.read.parquet("/data/silver/events_views").show(10, truncate=False)'

# Lire les données Gold (trending)
docker-compose exec spark-master /opt/spark/bin/spark-shell \
  --master spark://spark-master:7077 \
  -e 'spark.read.parquet("/data/gold/trending_now_1h").show(10, truncate=False)'
```

### 8. Vérifier les Checkpoints

```bash
# Vérifier les checkpoints (nécessaires pour la reprise)
docker-compose exec spark-master ls -R /data/_checkpoints/
```

### 9. Vérifier les Dead-Letters (si erreurs)

```bash
# Vérifier les événements invalides
docker-compose exec spark-master ls -R /data/silver/_deadletter/
```

## Commandes Utiles

### Voir les logs Spark Streaming

```bash
# Logs du job Kafka → Silver
docker-compose logs spark-master | grep -i "stream_kafka_to_silver"

# Logs du job Silver → Gold
docker-compose logs spark-master | grep -i "stream_trending_to_gold"
```

### Vérifier les métriques Kafka

```bash
# Consommateurs actifs
docker-compose exec kafka kafka-consumer-groups --bootstrap-server kafka:29092 --list

# Détails d'un groupe
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:29092 \
  --group spark-kafka-source \
  --describe
```

### Arrêter les Jobs Streaming

```bash
# Arrêter proprement (Ctrl+C dans les terminaux où les jobs tournent)
# Ou tuer les processus Spark
docker-compose exec spark-master pkill -f stream_kafka_to_silver
docker-compose exec spark-master pkill -f stream_trending_to_gold
```

## Dépannage

### Les événements ne sont pas traités

1. Vérifiez que les jobs Spark sont actifs (Spark UI)
2. Vérifiez les logs Spark pour des erreurs
3. Vérifiez que Kafka reçoit les messages (Kafka UI)
4. Vérifiez les checkpoints (peuvent être corrompus)

### Erreurs de connexion Kafka

```bash
# Vérifier que Kafka est accessible
docker-compose exec spark-master ping kafka

# Vérifier les ports
docker-compose ps kafka
```

### Données non visibles dans Silver/Gold

- Les données sont écrites par micro-batches (toutes les 10-30 secondes)
- Attendez quelques secondes après l'envoi d'événements
- Vérifiez les checkpoints pour voir si le traitement est bloqué

## Exemple Complet en Une Commande

```bash
# D'abord, installer les JARs Kafka (une seule fois)
./scripts/install_kafka_jars.sh  # ou .\scripts\install_kafka_jars.ps1 sur Windows

# Terminal 1: Job Kafka → Silver
docker-compose exec spark-master bash -c 'export STORAGE_FORMAT=parquet && export KAFKA_BOOTSTRAP_SERVERS=kafka:29092 && export LAKEHOUSE_PATH=/data && /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/stream_kafka_to_silver.py' &

# Terminal 2: Job Silver → Gold
docker-compose exec spark-master bash -c 'export STORAGE_FORMAT=parquet && export LAKEHOUSE_PATH=/data && /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/spark/jobs/stream_trending_to_gold.py' &

# Terminal 3: Générer des événements
docker run --rm -it \
  --network films-recommandation-system_bigdata-network \
  -v ${PWD}/tools:/app/tools \
  python:3.11-slim bash -c "
    pip install --no-cache-dir kafka-python==2.0.2 && \
    python /app/tools/generate_streaming_events.py \
      --bootstrap-servers kafka:29092 \
      --mode stream \
      --events-per-second 10 \
      --duration 60
  "
```

## Prochaines Étapes

Une fois que le streaming fonctionne :

1. **Monitorer** via Spark UI et Kafka UI
2. **Vérifier** les métriques de performance
3. **Tester** la reprise après arrêt (via checkpoints)
4. **Valider** la qualité des données dans Silver/Gold
5. **Intégrer** avec Airflow pour l'orchestration

