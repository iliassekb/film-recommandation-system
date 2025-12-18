# Fix: Création des Topics Kafka

Si la commande `docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:29092` n'affiche rien, les topics n'existent pas encore.

## Solution 1: Utiliser le Script Python (Recommandé)

Le script `tools/kafka_topic_init.py` crée automatiquement les topics :

```bash
docker run --rm \
  --network films-recommandation-system_bigdata-network \
  -v ${PWD}/tools:/app/tools \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  python:3.11-slim bash -c "
    pip install --no-cache-dir kafka-python==2.0.2 && \
    python /app/tools/kafka_topic_init.py
  "
```

## Solution 2: Créer les Topics Manuellement

Exécutez ces commandes une par une :

```bash
# Topic events_views
docker-compose exec kafka kafka-topics --create \
  --bootstrap-server localhost:29092 \
  --topic events_views \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000

# Topic events_clicks
docker-compose exec kafka kafka-topics --create \
  --bootstrap-server localhost:29092 \
  --topic events_clicks \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000

# Topic events_ratings
docker-compose exec kafka kafka-topics --create \
  --bootstrap-server localhost:29092 \
  --topic events_ratings \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=2592000000
```

## Vérification

Après création, vérifiez que les topics existent :

```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:29092
```

Vous devriez voir :
```
events_clicks
events_ratings
events_views
```

## Détails des Topics

- **events_views**: 3 partitions, rétention 7 jours
- **events_clicks**: 3 partitions, rétention 7 jours  
- **events_ratings**: 3 partitions, rétention 30 jours

## Alternative: Utiliser Kafka UI

1. Accédez à http://localhost:8080
2. Allez dans "Topics"
3. Cliquez sur "Add a Topic"
4. Créez chaque topic avec les paramètres ci-dessus

## Dépannage

### Erreur: "Connection refused"

Vérifiez que Kafka est démarré :
```bash
docker-compose ps kafka
docker-compose logs kafka --tail 20
```

### Erreur: "Topic already exists"

C'est normal, le topic existe déjà. Continuez avec les autres topics.

### Erreur: "Bootstrap server not available"

Attendez quelques secondes que Kafka soit complètement démarré, puis réessayez.




