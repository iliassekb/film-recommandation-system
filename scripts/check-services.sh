#!/bin/bash

# Script pour vérifier l'état de tous les services

echo "🔍 Vérification de l'état des services..."
echo ""

# Fonction pour vérifier un service
check_service() {
    local service=$1
    local port=$2
    local name=$3
    
    if docker-compose ps $service | grep -q "Up"; then
        if [ -n "$port" ]; then
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:$port > /dev/null 2>&1; then
                echo "✅ $name - En cours d'exécution (port $port)"
            else
                echo "⚠️  $name - Conteneur démarré mais port $port non accessible"
            fi
        else
            echo "✅ $name - En cours d'exécution"
        fi
    else
        echo "❌ $name - Arrêté"
    fi
}

# Vérifier tous les services
check_service "zookeeper" "" "Zookeeper"
check_service "kafka" "9092" "Kafka"
check_service "kafka-ui" "8080" "Kafka UI"
check_service "postgres" "5432" "PostgreSQL"
check_service "redis" "6379" "Redis"
check_service "spark-master" "8081" "Spark Master"
check_service "spark-worker-1" "" "Spark Worker 1"
check_service "spark-worker-2" "" "Spark Worker 2"
check_service "airflow-webserver" "8082" "Airflow Webserver"
check_service "airflow-scheduler" "" "Airflow Scheduler"
check_service "airflow-worker" "" "Airflow Worker"
check_service "mlflow" "5000" "MLflow"
check_service "prometheus" "9090" "Prometheus"
check_service "grafana" "3000" "Grafana"
check_service "fastapi" "8000" "FastAPI"

echo ""
echo "📊 Résumé:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

