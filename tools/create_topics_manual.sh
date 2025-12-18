#!/bin/bash
# Script pour créer manuellement les topics Kafka

echo "🔧 Création des topics Kafka..."

# Créer events_views
docker-compose exec kafka kafka-topics --create \
  --bootstrap-server localhost:29092 \
  --topic events_views \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --if-not-exists

# Créer events_clicks
docker-compose exec kafka kafka-topics --create \
  --bootstrap-server localhost:29092 \
  --topic events_clicks \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --if-not-exists

# Créer events_ratings
docker-compose exec kafka kafka-topics --create \
  --bootstrap-server localhost:29092 \
  --topic events_ratings \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=2592000000 \
  --if-not-exists

echo "✅ Topics créés!"

# Lister les topics
echo ""
echo "📋 Liste des topics:"
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:29092




