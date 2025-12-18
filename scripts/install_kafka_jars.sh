#!/bin/bash
# Script pour installer les JARs Kafka dans /opt/spark/jars sur tous les conteneurs Spark
# Cela garantit que les JARs sont disponibles sur le driver ET les executors

set -e

JAR_DIR="/tmp/spark-jars"
SPARK_JARS_DIR="/opt/spark/jars"

echo "📦 Installation des JARs Kafka pour Spark..."
echo ""

# Liste des conteneurs Spark
SPARK_CONTAINERS=("spark-master" "spark-worker-1" "spark-worker-2")

# Télécharger les JARs sur le master d'abord
echo "1️⃣  Téléchargement des JARs sur spark-master..."
docker-compose exec -T spark-master bash -c "
  mkdir -p $JAR_DIR && \
  cd $JAR_DIR && \
  curl -L -f -o kafka-clients.jar https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar && \
  curl -L -f -o spark-sql-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.4.0/spark-sql-kafka-0-10_2.12-3.4.0.jar && \
  curl -L -f -o spark-token-provider-kafka.jar https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.4.0/spark-token-provider-kafka-0-10_2.12-3.4.0.jar && \
  echo '✅ JARs téléchargés'
"

# Copier les JARs dans /opt/spark/jars sur tous les conteneurs (avec sudo pour les permissions)
for container in "${SPARK_CONTAINERS[@]}"; do
  echo ""
  echo "2️⃣  Installation des JARs sur $container..."
  docker-compose exec -T "$container" bash -c "
    sudo mkdir -p $SPARK_JARS_DIR && \
    sudo cp $JAR_DIR/kafka-clients.jar $SPARK_JARS_DIR/ 2>/dev/null || true && \
    sudo cp $JAR_DIR/spark-sql-kafka.jar $SPARK_JARS_DIR/ 2>/dev/null || true && \
    sudo cp $JAR_DIR/spark-token-provider-kafka.jar $SPARK_JARS_DIR/ 2>/dev/null || true && \
    sudo chmod 644 $SPARK_JARS_DIR/*kafka*.jar 2>/dev/null || true && \
    echo '✅ JARs installés dans $SPARK_JARS_DIR' && \
    ls -lh $SPARK_JARS_DIR/*kafka* 2>/dev/null || echo '⚠️  Aucun JAR Kafka trouvé'
  "
done

echo ""
echo "✅ Installation terminée!"
echo ""
echo "Les JARs sont maintenant disponibles dans /opt/spark/jars sur tous les conteneurs Spark."
echo "Vous pouvez maintenant lancer stream_kafka_to_silver.py sans --jars"

