# Fix: NoClassDefFoundError - Kafka JARs sur les Executors

## Problème

Lors de l'exécution de `stream_kafka_to_silver.py`, vous obtenez l'erreur :

```
java.lang.NoClassDefFoundError: Could not initialize class org.apache.spark.sql.kafka010.consumer.KafkaDataConsumer$
```

Cette erreur se produit parce que les JARs Kafka ne sont pas disponibles sur les **executors** (spark-worker-1, spark-worker-2).

## Cause

Quand vous utilisez `--jars` avec `spark-submit`, les JARs sont seulement disponibles sur le **driver** (spark-master). Les executors n'ont pas automatiquement accès à ces JARs, sauf si Spark les distribue correctement (ce qui peut échouer dans certains cas).

## Solution

Installez les JARs Kafka dans `/opt/spark/jars` sur **tous** les conteneurs Spark (master et workers). Ce répertoire est automatiquement dans le classpath de Spark.

### Option 1: Utiliser le Script Automatique (Recommandé)

**Sur Linux/Mac:**
```bash
chmod +x scripts/install_kafka_jars.sh
./scripts/install_kafka_jars.sh
```

**Sur Windows (PowerShell):**
```powershell
.\scripts\install_kafka_jars.ps1
```

### Option 2: Installation Manuelle

```bash
# 1. Télécharger les JARs sur le master
docker-compose exec spark-master bash -c '
  mkdir -p /tmp/spark-jars && \
  cd /tmp/spark-jars && \
  curl -L -o kafka-clients.jar https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar && \
  curl -L -o spark-sql-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.4.0/spark-sql-kafka-0-10_2.12-3.4.0.jar && \
  curl -L -o spark-token-provider-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.4.0/spark-token-provider-kafka-0-10_2.12-3.4.0.jar
'

# 2. Copier dans /opt/spark/jars sur tous les conteneurs (avec sudo pour les permissions)
for container in spark-master spark-worker-1 spark-worker-2; do
  echo "Installation sur $container..."
  docker-compose exec $container bash -c '
    sudo mkdir -p /opt/spark/jars && \
    sudo cp /tmp/spark-jars/kafka-clients.jar /opt/spark/jars/ && \
    sudo cp /tmp/spark-jars/spark-sql-kafka.jar /opt/spark/jars/ && \
    sudo cp /tmp/spark-jars/spark-token-provider-kafka.jar /opt/spark/jars/ && \
    sudo chmod 644 /opt/spark/jars/*kafka*.jar && \
    ls -lh /opt/spark/jars/*kafka*
  '
done
```

## Vérification

Vérifiez que les JARs sont installés :

```bash
# Sur le master
docker-compose exec spark-master ls -lh /opt/spark/jars/*kafka*

# Sur les workers
docker-compose exec spark-worker-1 ls -lh /opt/spark/jars/*kafka*
docker-compose exec spark-worker-2 ls -lh /opt/spark/jars/*kafka*
```

Vous devriez voir :
- `kafka-clients.jar`
- `spark-sql-kafka.jar`
- `spark-token-provider-kafka.jar`

## Lancer le Job

Après l'installation, vous pouvez lancer le job **sans** `--jars` :

```bash
docker-compose exec spark-master bash -c '
  export STORAGE_FORMAT=parquet && \
  export KAFKA_BOOTSTRAP_SERVERS=kafka:29092 && \
  export LAKEHOUSE_PATH=/data && \
  /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    /opt/spark/jobs/stream_kafka_to_silver.py
'
```

## Notes Importantes

1. **Une seule fois**: L'installation doit être faite une seule fois, sauf si vous recréez les conteneurs.

2. **Persistance**: Les JARs dans `/opt/spark/jars` persistent tant que les conteneurs ne sont pas recréés. Si vous faites `docker-compose down` puis `docker-compose up`, vous devrez réinstaller.

3. **Alternative avec volumes**: Pour une persistance permanente, vous pouvez ajouter un volume partagé dans `docker-compose.yml` :

```yaml
spark-master:
  volumes:
    - kafka-jars:/opt/spark/jars
    # ... autres volumes

spark-worker-1:
  volumes:
    - kafka-jars:/opt/spark/jars
    # ... autres volumes

spark-worker-2:
  volumes:
    - kafka-jars:/opt/spark/jars
    # ... autres volumes

volumes:
  kafka-jars:
```

Puis installez les JARs une fois dans ce volume partagé.

## Dépannage

### Les JARs ne sont pas trouvés après installation

1. Vérifiez que les conteneurs sont bien démarrés : `docker-compose ps`
2. Vérifiez les permissions : `docker-compose exec spark-master ls -la /opt/spark/jars`
3. Redémarrez les conteneurs Spark : `docker-compose restart spark-master spark-worker-1 spark-worker-2`

### Erreur "Permission denied"

Les JARs doivent être accessibles en lecture. Si nécessaire :
```bash
docker-compose exec spark-master chmod 644 /opt/spark/jars/*.jar
```

