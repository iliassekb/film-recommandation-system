#!/bin/bash
# Script pour exécuter le streaming Kafka → Console en mode LOCAL
# Mode local = exécution sur le driver uniquement (pas besoin de workers ou de JARs installés)
# Utile pour tester avec des ressources limitées

KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-"kafka:29092"}
STORAGE_FORMAT=${STORAGE_FORMAT:-"parquet"}
LAKEHOUSE_PATH=${LAKEHOUSE_PATH:-"/data"}

echo "🚀 Démarrage du streaming Kafka → Console (MODE LOCAL)"
echo "   Kafka: $KAFKA_BOOTSTRAP_SERVERS"
echo "   Mode: LOCAL (exécution sur driver uniquement)"
echo "   Topics: events_views, events_clicks, events_ratings"
echo ""
echo "📡 Les événements seront affichés dans la console toutes les 2 secondes"
echo "   Appuyez sur Ctrl+C pour arrêter"
echo ""
echo "ℹ️  Mode LOCAL utilise --packages pour télécharger automatiquement les JARs Kafka"
echo "   Pas besoin d'installer les JARs manuellement"
echo ""

# Mode local - exécute tout sur le driver avec --packages
docker-compose exec spark-master bash -c "
    export KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS && \
    export STORAGE_FORMAT=$STORAGE_FORMAT && \
    export LAKEHOUSE_PATH=$LAKEHOUSE_PATH && \
    /opt/spark/bin/spark-submit \
        --master local[2] \
        --deploy-mode client \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0 \
        --conf spark.sql.adaptive.enabled=true \
        --conf spark.sql.adaptive.coalescePartitions.enabled=true \
        /opt/spark/jobs/stream_kafka_console.py
"

