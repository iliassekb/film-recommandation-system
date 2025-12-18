# Fix: Erreur Spark Ivy Cache

## Problème

Erreur lors de l'exécution de `spark-submit` avec `--packages`:
```
java.io.FileNotFoundException: /opt/spark/.ivy2/cache/resolved-...xml (No such file or directory)
```

Spark essaie d'écrire dans `/opt/spark/.ivy2` qui nécessite des permissions root.

## Solution Recommandée: Télécharger les JARs Manuellement

Au lieu d'utiliser `--packages` (qui nécessite Ivy), téléchargez tous les JARs nécessaires manuellement et utilisez `--jars`:

```bash
docker-compose exec spark-master bash -c '
  mkdir -p /tmp/spark-jars && \
  cd /tmp/spark-jars && \
  curl -L -o kafka-clients.jar https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar && \
  curl -L -o spark-sql-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.4.0/spark-sql-kafka-0-10_2.12-3.4.0.jar && \
  curl -L -o spark-token-provider-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.4.0/spark-token-provider-kafka-0-10_2.12-3.4.0.jar && \
  export STORAGE_FORMAT=parquet && \
  export KAFKA_BOOTSTRAP_SERVERS=kafka:29092 && \
  export LAKEHOUSE_PATH=/data && \
  /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --jars /tmp/spark-jars/kafka-clients.jar,/tmp/spark-jars/spark-sql-kafka.jar,/tmp/spark-jars/spark-token-provider-kafka.jar \
    /opt/spark/jobs/stream_kafka_to_silver.py
'
```

**JARs requis:**
- `kafka-clients-3.4.0.jar` - Client Kafka (dépendance principale)
- `spark-sql-kafka-0-10_2.12-3.4.0.jar` - Intégration Spark-Kafka
- `spark-token-provider-kafka-0-10_2.12-3.4.0.jar` - Provider de tokens pour Kafka

## Alternative: Utiliser un Volume Docker

Ajoutez un volume pour `/opt/spark/.ivy2` dans `docker-compose.yml`:

```yaml
spark-master:
  volumes:
    - spark-ivy-cache:/opt/spark/.ivy2
    # ... autres volumes

volumes:
  spark-ivy-cache:
```

Puis recréez le conteneur:
```bash
docker-compose up -d --force-recreate spark-master
```

## Alternative: Pré-télécharger les Packages

Téléchargez les packages une fois avec un utilisateur root:

```bash
docker-compose exec -u root spark-master bash -c "
  mkdir -p /opt/spark/.ivy2/cache /opt/spark/.ivy2/jars && \
  chown -R spark:spark /opt/spark/.ivy2 && \
  su - spark -c '/opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 --version || true'
"
```

Puis utilisez normalement `--packages` dans les commandes suivantes.

## Vérification

Après avoir téléchargé le JAR, vérifiez:

```bash
docker-compose exec spark-master ls -lh /tmp/spark-jars/
```

Vous devriez voir `spark-sql-kafka.jar`.
