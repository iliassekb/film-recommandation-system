# Guide Docker - Kafka et Spark Streaming

## Démarrage rapide avec Docker

### 1. Démarrer Kafka et Zookeeper

```bash
docker-compose up -d
```

Cela démarre:
- **Zookeeper** sur le port 2181
- **Kafka** sur le port 9092
- **Kafka UI** sur le port 8080 (interface web pour visualiser les topics)

### 2. Vérifier que les services sont démarrés

```bash
docker-compose ps
```

Vous devriez voir `kafka`, `zookeeper` et `kafka-ui` avec le statut "Up".

### 3. Accéder à Kafka UI

Ouvrez votre navigateur sur: http://localhost:8080

Vous pouvez y voir:
- Les topics créés
- Les messages dans chaque topic
- Les consommateurs actifs

### 4. Créer les topics (optionnel)

Les topics sont créés automatiquement, mais vous pouvez les créer manuellement:

```bash
python create_topics.py
```

### 5. Démarrer le producteur (local)

Dans un terminal, démarrez le générateur de données:

```bash
python producer.py
```

Les données seront envoyées aux topics Kafka.

### 6. Démarrer le consumer Spark Streaming (Docker)

**Option A: Avec docker-compose (recommandé)**

```bash
docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer
```

**Option B: Build et run manuel**

```bash
# Construire l'image
docker build -f Dockerfile.spark -t spark-consumer .

# Lancer le container
docker run --network kafka-streaming_kafka-network \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
  -v ${PWD}/data:/opt/bitnami/spark/work/data \
  -v ${PWD}/checkpoints:/opt/bitnami/spark/work/checkpoints \
  spark-consumer
```

### 7. Vérifier les fichiers Parquet

Les fichiers Parquet sont créés dans:
- `data/parquet/clicks/`
- `data/parquet/views/`
- `data/parquet/ratings/`

Ils sont créés toutes les 10 secondes.

## Commandes utiles

### Voir les logs Kafka
```bash
docker-compose logs -f kafka
```

### Voir les logs Spark Consumer
```bash
docker-compose logs -f spark-consumer
```

### Arrêter tous les services
```bash
docker-compose down
```

### Arrêter uniquement Spark
```bash
docker-compose -f docker-compose.yml -f docker-compose.spark.yml stop spark-consumer
```

### Redémarrer un service
```bash
docker-compose restart kafka
```

### Supprimer les données (volumes)
```bash
docker-compose down -v
```

⚠️ **Attention**: Cela supprimera toutes les données Kafka stockées.

### Voir les topics Kafka dans le container
```bash
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Consulter les messages d'un topic
```bash
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic clicks --from-beginning
```

## Résolution de problèmes

### Kafka ne démarre pas

Vérifiez que le port 9092 n'est pas déjà utilisé:
```bash
# Windows
netstat -ano | findstr :9092

# Linux/Mac
lsof -i :9092
```

### Spark ne peut pas se connecter à Kafka

Vérifiez que:
1. Kafka est bien démarré: `docker-compose ps`
2. Les deux containers sont sur le même réseau: `docker network ls`
3. La variable d'environnement `KAFKA_BOOTSTRAP_SERVERS` est correcte: `kafka:29092` (depuis Docker) ou `localhost:9092` (depuis la machine locale)

### Les fichiers Parquet ne sont pas créés

Vérifiez:
1. Les permissions des dossiers `data/` et `checkpoints/`
2. Les logs du container Spark: `docker-compose logs spark-consumer`
3. Que des données sont bien envoyées à Kafka (vérifier dans Kafka UI)

## Configuration réseau Docker

Les services communiquent via le réseau `kafka-network`:
- Kafka expose `localhost:9092` pour les connexions depuis la machine hôte
- Kafka expose `kafka:29092` pour les connexions depuis d'autres containers Docker
- Spark consumer utilise `kafka:29092` pour se connecter depuis le container

## Variables d'environnement

### Producer (local)
- `KAFKA_BOOTSTRAP_SERVERS`: `localhost:9092` (par défaut)

### Spark Consumer (Docker)
- `KAFKA_BOOTSTRAP_SERVERS`: `kafka:29092` (configuré dans docker-compose.spark.yml)


