# Script PowerShell pour exécuter le streaming Kafka → Console depuis un conteneur Spark

$KAFKA_BOOTSTRAP_SERVERS = if ($env:KAFKA_BOOTSTRAP_SERVERS) { $env:KAFKA_BOOTSTRAP_SERVERS } else { "kafka:29092" }
$SPARK_MASTER = if ($env:SPARK_MASTER) { $env:SPARK_MASTER } else { "spark://spark-master:7077" }
$STORAGE_FORMAT = if ($env:STORAGE_FORMAT) { $env:STORAGE_FORMAT } else { "parquet" }
$LAKEHOUSE_PATH = if ($env:LAKEHOUSE_PATH) { $env:LAKEHOUSE_PATH } else { "/data" }

Write-Host "🚀 Démarrage du streaming Kafka → Console" -ForegroundColor Cyan
Write-Host "   Kafka: $KAFKA_BOOTSTRAP_SERVERS"
Write-Host "   Spark Master: $SPARK_MASTER"
Write-Host "   Topics: events_views, events_clicks, events_ratings"
Write-Host ""
Write-Host "📡 Les événements seront affichés dans la console toutes les 2 secondes" -ForegroundColor Yellow
Write-Host "   Appuyez sur Ctrl+C pour arrêter"
Write-Host ""

# Exécuter le job Spark
docker-compose exec spark-master bash -c @"
    export KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS && \
    export STORAGE_FORMAT=$STORAGE_FORMAT && \
    export LAKEHOUSE_PATH=$LAKEHOUSE_PATH && \
    /opt/spark/bin/spark-submit \
        --master $SPARK_MASTER \
        --deploy-mode client \
        --conf spark.sql.adaptive.enabled=true \
        --conf spark.sql.adaptive.coalescePartitions.enabled=true \
        /opt/spark/jobs/stream_kafka_console.py
"@

