# Guide Rapide - Génération d'Événements Streaming

## Méthode 1: Utiliser docker-compose (Recommandé)

Cette méthode utilise le service `kafka-topic-init` qui est déjà configuré avec le bon réseau.

### Mode Batch (100 événements)

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

### Mode Stream Continu (5ms entre événements, Ctrl+C pour arrêter)

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

**Note**: 
- Génère un événement toutes les 5ms (~200 événements/seconde)
- Affiche chaque événement généré
- Ne s'arrête que sur Ctrl+C
- Les micro-batches Spark traitent toutes les 5 secondes

## Méthode 2: Utiliser le réseau Docker directement

### Trouver le nom du réseau

```powershell
# PowerShell
$networkName = docker network ls | Select-String "bigdata" | ForEach-Object { $_.ToString().Split()[1] }
Write-Host "Network: $networkName"
```

### Exécuter le script

```powershell
docker run --rm -it `
  --network $networkName `
  -v ${PWD}/tools:/app/tools `
  python:3.11-slim bash -c "
    pip install --no-cache-dir kafka-python==2.0.2 && \
    python /app/tools/generate_streaming_events.py \
      --bootstrap-servers kafka:29092 \
      --mode batch \
      --num-events 100
  "
```

## Méthode 3: Depuis votre machine (si Python installé)

```bash
# Installer la dépendance
pip install kafka-python

# Exécuter le script
python tools/generate_streaming_events.py \
  --bootstrap-servers localhost:9092 \
  --mode batch \
  --num-events 100
```

## Vérification

Après avoir généré des événements, vérifiez dans Kafka UI: http://localhost:8080

Les messages devraient apparaître dans les topics:
- `events_views`
- `events_clicks`
- `events_ratings`

