#!/bin/bash
# Script pour télécharger tous les JARs Kafka nécessaires pour Spark

JAR_DIR="/tmp/spark-jars"
mkdir -p "$JAR_DIR"
cd "$JAR_DIR"

echo "📦 Téléchargement des JARs Kafka pour Spark..."

# Kafka Clients (dépendance principale)
echo "  - kafka-clients..."
curl -L -o kafka-clients.jar \
  https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar

# Spark SQL Kafka
echo "  - spark-sql-kafka..."
curl -L -o spark-sql-kafka.jar \
  https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.4.0/spark-sql-kafka-0-10_2.12-3.4.0.jar

# Spark Token Provider Kafka
echo "  - spark-token-provider-kafka..."
curl -L -o spark-token-provider-kafka.jar \
  https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.4.0/spark-token-provider-kafka-0-10_2.12-3.4.0.jar

echo "✅ Tous les JARs ont été téléchargés dans $JAR_DIR"
ls -lh "$JAR_DIR"




