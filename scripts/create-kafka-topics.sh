#!/bin/bash

# Script pour créer les topics Kafka nécessaires au système de recommandation

KAFKA_CONTAINER="kafka"
BOOTSTRAP_SERVER="localhost:9092"

echo " topic Kafka pour le système de recommandation de films..."
echo ""

# Fonction pour créer un topic
create_topic() {
    local topic_name=$1
    local partitions=${2:-3}
    local replication_factor=${3:-1}
    
    echo "Création du topic: $topic_name (partitions: $partitions, replication: $replication_factor)"
    
    docker-compose exec -T $KAFKA_CONTAINER kafka-topics \
        --create \
        --topic $topic_name \
        --bootstrap-server $BOOTSTRAP_SERVER \
        --partitions $partitions \
        --replication-factor $replication_factor \
        2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Topic '$topic_name' créé avec succès"
    else
        echo "ℹ️  Topic '$topic_name' existe déjà ou erreur"
    fi
    echo ""
}

# Créer les topics
create_topic "film-ratings" 3 1
create_topic "film-recommendations" 3 1
create_topic "user-events" 3 1
create_topic "film-updates" 3 1

echo "📋 Liste des topics existants:"
docker-compose exec -T $KAFKA_CONTAINER kafka-topics \
    --list \
    --bootstrap-server $BOOTSTRAP_SERVER

echo ""
echo "✅ Création des topics terminée!"

