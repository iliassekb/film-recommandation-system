#!/bin/bash

# Script d'initialisation pour le système de recommandation de films
# Ce script crée les bases de données nécessaires et initialise les services

echo "🚀 Initialisation du système de recommandation de films..."
echo ""

# Vérifier si Docker est en cours d'exécution
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker n'est pas en cours d'exécution. Veuillez démarrer Docker Desktop."
    exit 1
fi

echo "✅ Docker est en cours d'exécution"
echo ""

# Démarrer PostgreSQL en premier
echo "📦 Démarrage de PostgreSQL..."
docker-compose up -d postgres

# Attendre que PostgreSQL soit prêt
echo "⏳ Attente de PostgreSQL..."
sleep 10

# Vérifier que PostgreSQL est prêt
until docker-compose exec -T postgres pg_isready -U airflow > /dev/null 2>&1; do
    echo "⏳ En attente de PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL est prêt"
echo ""

# Créer la base de données MLflow
echo "📊 Création de la base de données MLflow..."
docker-compose exec -T postgres psql -U airflow -c "CREATE DATABASE mlflow;" 2>/dev/null || echo "ℹ️  La base de données MLflow existe déjà"
echo "✅ Base de données MLflow créée"
echo ""

# Démarrer tous les services
echo "🚀 Démarrage de tous les services..."
docker-compose up -d

echo ""
echo "✅ Tous les services sont en cours de démarrage!"
echo ""
echo "📋 Accès aux services:"
echo "   - Kafka UI:        http://localhost:8080"
echo "   - Spark Master:    http://localhost:8081"
echo "   - Airflow:         http://localhost:8082 (admin/admin)"
echo "   - MLflow:          http://localhost:5000"
echo "   - Grafana:         http://localhost:3000 (admin/admin)"
echo "   - Prometheus:      http://localhost:9090"
echo "   - FastAPI:         http://localhost:8000"
echo "   - FastAPI Docs:    http://localhost:8000/docs"
echo ""
echo "⏳ Attendez quelques instants que tous les services soient prêts..."
echo "   Vous pouvez vérifier l'état avec: docker-compose ps"
echo "   Voir les logs avec: docker-compose logs -f [service-name]"
echo ""

