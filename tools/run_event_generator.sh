#!/bin/bash
# Script pour exécuter le générateur d'événements depuis un conteneur Docker

KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-"kafka:29092"}
MODE=${MODE:-"batch"}
NUM_EVENTS=${NUM_EVENTS:-100}
EVENTS_PER_SECOND=${EVENTS_PER_SECOND:-10.0}
DURATION=${DURATION:-""}

echo "🚀 Génération d'événements de streaming"
echo "   Kafka: $KAFKA_BOOTSTRAP_SERVERS"
echo "   Mode: $MODE"

if [ "$MODE" = "batch" ]; then
    python3 /app/tools/generate_streaming_events.py \
        --bootstrap-servers "$KAFKA_BOOTSTRAP_SERVERS" \
        --mode batch \
        --num-events "$NUM_EVENTS"
else
    if [ -n "$DURATION" ]; then
        python3 /app/tools/generate_streaming_events.py \
            --bootstrap-servers "$KAFKA_BOOTSTRAP_SERVERS" \
            --mode stream \
            --events-per-second "$EVENTS_PER_SECOND" \
            --duration "$DURATION"
    else
        python3 /app/tools/generate_streaming_events.py \
            --bootstrap-servers "$KAFKA_BOOTSTRAP_SERVERS" \
            --mode stream \
            --events-per-second "$EVENTS_PER_SECOND"
    fi
fi




