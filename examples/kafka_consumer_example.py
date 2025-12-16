"""
Exemple de consommateur Kafka pour lire des données de ratings de films
Ce script montre comment consommer des données depuis Kafka
"""

from kafka import KafkaConsumer
import json
from datetime import datetime

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"  # Depuis l'hôte
# KAFKA_BOOTSTRAP_SERVERS = "kafka:29092"  # Depuis un conteneur Docker

TOPIC_RATINGS = "film-ratings"
TOPIC_EVENTS = "user-events"

def create_consumer(topic, group_id="film-recommendation-group", auto_offset_reset="latest"):
    """
    Créer un consommateur Kafka
    
    Args:
        topic: Nom du topic à consommer
        group_id: ID du groupe de consommateurs
        auto_offset_reset: Où commencer à lire ("earliest" ou "latest")
    
    Returns:
        KafkaConsumer
    """
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        key_deserializer=lambda k: k.decode('utf-8') if k else None,
        consumer_timeout_ms=10000  # Timeout de 10 secondes
    )
    return consumer

def consume_ratings(limit=None):
    """
    Consommer des ratings depuis Kafka
    
    Args:
        limit: Nombre maximum de messages à consommer (None pour illimité)
    """
    print(f"📡 Consommation des ratings depuis le topic '{TOPIC_RATINGS}'...")
    print("   Appuyez sur Ctrl+C pour arrêter\n")
    
    consumer = create_consumer(TOPIC_RATINGS, group_id="ratings-consumer-group")
    
    count = 0
    try:
        for message in consumer:
            rating_data = message.value
            print(f"📥 Message reçu:")
            print(f"   Partition: {message.partition}, Offset: {message.offset}")
            print(f"   Key: {message.key}")
            print(f"   Value: {rating_data}")
            print()
            
            count += 1
            if limit and count >= limit:
                print(f"✅ {count} messages consommés. Arrêt...")
                break
                
    except KeyboardInterrupt:
        print(f"\n⏹️  Arrêt du consommateur. {count} messages consommés.")
    finally:
        consumer.close()

def consume_events(limit=None):
    """
    Consommer des événements utilisateur depuis Kafka
    
    Args:
        limit: Nombre maximum de messages à consommer (None pour illimité)
    """
    print(f"📡 Consommation des événements depuis le topic '{TOPIC_EVENTS}'...")
    print("   Appuyez sur Ctrl+C pour arrêter\n")
    
    consumer = create_consumer(TOPIC_EVENTS, group_id="events-consumer-group")
    
    count = 0
    try:
        for message in consumer:
            event_data = message.value
            print(f"📥 Événement reçu:")
            print(f"   Partition: {message.partition}, Offset: {message.offset}")
            print(f"   User ID: {event_data.get('user_id')}")
            print(f"   Event Type: {event_data.get('event_type')}")
            print(f"   Film ID: {event_data.get('film_id')}")
            print(f"   Timestamp: {event_data.get('timestamp')}")
            print()
            
            count += 1
            if limit and count >= limit:
                print(f"✅ {count} événements consommés. Arrêt...")
                break
                
    except KeyboardInterrupt:
        print(f"\n⏹️  Arrêt du consommateur. {count} événements consommés.")
    finally:
        consumer.close()

def process_ratings_batch(batch_size=100):
    """
    Traiter les ratings par batch
    
    Args:
        batch_size: Taille du batch
    """
    print(f"📊 Traitement des ratings par batch de {batch_size}...")
    
    consumer = create_consumer(TOPIC_RATINGS, group_id="batch-processor-group")
    
    batch = []
    count = 0
    
    try:
        for message in consumer:
            batch.append(message.value)
            
            if len(batch) >= batch_size:
                # Traiter le batch
                print(f"🔄 Traitement d'un batch de {len(batch)} ratings...")
                
                # Ici vous pouvez faire votre traitement
                # Par exemple: calculer des statistiques, sauvegarder en base, etc.
                avg_rating = sum(r['rating'] for r in batch) / len(batch)
                print(f"   Note moyenne du batch: {avg_rating:.2f}")
                
                batch = []
                count += batch_size
                
    except KeyboardInterrupt:
        if batch:
            print(f"\n🔄 Traitement du dernier batch de {len(batch)} ratings...")
            count += len(batch)
        print(f"\n⏹️  Arrêt. {count} ratings traités au total.")
    finally:
        consumer.close()

def main():
    """Fonction principale"""
    import sys
    
    print("🚀 Consommateur Kafka - Système de Recommandation de Films")
    print(f"📡 Connexion à Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print()
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "ratings"
    
    try:
        if mode == "ratings":
            consume_ratings(limit=10)  # Consommer 10 messages par défaut
        elif mode == "events":
            consume_events(limit=10)
        elif mode == "batch":
            process_ratings_batch(batch_size=10)
        elif mode == "stream":
            # Mode streaming (illimité)
            consume_ratings(limit=None)
        else:
            print(f"❌ Mode inconnu: {mode}")
            print("   Modes disponibles: ratings, events, batch, stream")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\n💡 Vérifiez que:")
        print("   - Kafka est démarré: docker-compose ps kafka")
        print("   - Les topics existent: docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092")
        print("   - Vous utilisez le bon bootstrap server")

if __name__ == "__main__":
    main()

