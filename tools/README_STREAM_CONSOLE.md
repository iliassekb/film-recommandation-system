# Streaming Kafka → Console

Ce script permet de capturer et afficher en temps réel les événements des 3 topics Kafka :
- `events_views` - Événements de visualisation de films
- `events_clicks` - Événements de clics utilisateurs
- `events_ratings` - Événements de notation de films

## Prérequis

1. Les services Docker doivent être démarrés :
   ```bash
   docker-compose up -d
   ```

2. Les topics Kafka doivent exister :
   ```bash
   # Vérifier les topics
   docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:29092
   
   # Si les topics n'existent pas, les créer
   python tools/kafka_topic_init.py
   # ou
   docker-compose exec kafka-topic-init python /app/tools/kafka_topic_init.py
   ```

3. Le générateur d'événements doit être en cours d'exécution (optionnel mais recommandé pour voir des données) :
   ```bash
   # Dans un terminal séparé
   docker-compose run --rm \
     -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
     kafka-topic-init sh -c "
       pip install --no-cache-dir kafka-python==2.0.2 && \
       python3 /app/tools/run_event_generator.py \
         --mode stream \
         --interval-ms 5
     "
   ```

## Utilisation

### Linux/Mac (bash)

```bash
./tools/run_stream_console.sh
```

### Windows (PowerShell)

```powershell
.\tools\run_stream_console.ps1
```

### Exécution directe dans le conteneur Spark

```bash
docker-compose exec spark-master bash -c "
  export KAFKA_BOOTSTRAP_SERVERS=kafka:29092 && \
  export STORAGE_FORMAT=parquet && \
  export LAKEHOUSE_PATH=/data && \
  /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --conf spark.sql.adaptive.enabled=true \
    --conf spark.sql.adaptive.coalescePartitions.enabled=true \
    /opt/spark/jobs/stream_kafka_console.py
"
```

## Comportement

- Le script lit depuis les 3 topics Kafka en parallèle
- Les événements sont affichés dans la console toutes les 2 secondes
- Chaque événement affiche :
  - Le topic d'origine
  - Tous les champs de l'événement (event_id, event_type, user_id, movie_id, etc.)
  - Le timestamp Kafka

## Arrêt

Appuyez sur **Ctrl+C** pour arrêter le streaming.

## Notes

- Le script utilise `startingOffsets: latest`, donc il ne lit que les nouveaux événements après le démarrage
- Pour lire depuis le début des topics, modifiez le script pour utiliser `startingOffsets: earliest`
- Les données sont affichées dans la console uniquement, elles ne sont pas sauvegardées
- Pour sauvegarder les données, utilisez `stream_kafka_to_silver.py` à la place

