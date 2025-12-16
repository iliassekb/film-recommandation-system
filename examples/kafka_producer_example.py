"""
Exemple de producteur Kafka pour envoyer des données de ratings de films
Ce script montre comment publier des données vers Kafka
"""

from kafka import KafkaProducer
import json
import time
from datetime import datetime
import random

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"  # Depuis l'hôte
# KAFKA_BOOTSTRAP_SERVERS = "kafka:29092"  # Depuis un conteneur Docker

TOPIC_RATINGS = "film-ratings"
TOPIC_EVENTS = "user-events"

def create_producer():
    """Créer un producteur Kafka"""
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: str(k).encode('utf-8') if k else None,
        acks='all',  # Attendre la confirmation de tous les réplicas
        retries=3,
        max_in_flight_requests_per_connection=1
    )
    return producer

def send_film_rating(producer, user_id, film_id, rating):
    """
    Envoyer un rating de film vers Kafka
    
    Args:
        producer: KafkaProducer
        user_id: ID de l'utilisateur
        film_id: ID du film
        rating: Note (0.0 à 5.0)
    """
    message = {
        "user_id": user_id,
        "film_id": film_id,
        "rating": rating,
        "timestamp": datetime.now().isoformat()
    }
    
    # Utiliser user_id comme clé pour garantir l'ordre par utilisateur
    future = producer.send(
        TOPIC_RATINGS,
        key=user_id,
        value=message
    )
    
    # Attendre la confirmation
    try:
        record_metadata = future.get(timeout=10)
        print(f"✅ Rating envoyé - User: {user_id}, Film: {film_id}, Rating: {rating}")
        print(f"   Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi: {e}")
    
    return future

def send_user_event(producer, user_id, event_type, film_id=None):
    """
    Envoyer un événement utilisateur vers Kafka
    
    Args:
        producer: KafkaProducer
        user_id: ID de l'utilisateur
        event_type: Type d'événement (view, click, search, etc.)
        film_id: ID du film (optionnel)
    """
    message = {
        "user_id": user_id,
        "event_type": event_type,
        "film_id": film_id,
        "timestamp": datetime.now().isoformat()
    }
    
    future = producer.send(
        TOPIC_EVENTS,
        key=user_id,
        value=message
    )
    
    try:
        record_metadata = future.get(timeout=10)
        print(f"✅ Événement envoyé - User: {user_id}, Type: {event_type}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi: {e}")
    
    return future

def generate_sample_data(producer, num_ratings=100):
    """
    Générer et envoyer des données d'exemple
    
    Args:
        producer: KafkaProducer
        num_ratings: Nombre de ratings à générer
    """
    print(f"📊 Génération de {num_ratings} ratings d'exemple...")
    
    # Simuler des ratings de différents utilisateurs
    users = list(range(1, 21))  # 20 utilisateurs
    films = list(range(1, 51))  # 50 films
    
    for i in range(num_ratings):
        user_id = random.choice(users)
        film_id = random.choice(films)
        rating = round(random.uniform(1.0, 5.0), 1)
        
        send_film_rating(producer, user_id, film_id, rating)
        
        # Simuler aussi quelques événements
        if random.random() < 0.3:  # 30% de chance
            event_type = random.choice(["view", "click", "search"])
            send_user_event(producer, user_id, event_type, film_id)
        
        time.sleep(0.1)  # Petite pause entre les envois
    
    # S'assurer que tous les messages sont envoyés
    producer.flush()
    print(f"\n✅ {num_ratings} ratings envoyés avec succès!")

def main():
    """Fonction principale"""
    print("🚀 Producteur Kafka - Système de Recommandation de Films")
    print(f"📡 Connexion à Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"📝 Topics: {TOPIC_RATINGS}, {TOPIC_EVENTS}")
    print()
    
    try:
        # Créer le producteur
        producer = create_producer()
        print("✅ Connecté à Kafka")
        print()
        
        # Générer des données d'exemple
        generate_sample_data(producer, num_ratings=50)
        
        # Exemple d'envoi manuel
        print("\n📤 Envoi d'exemples manuels...")
        send_film_rating(producer, user_id=1, film_id=1, rating=4.5)
        send_film_rating(producer, user_id=1, film_id=2, rating=3.0)
        send_user_event(producer, user_id=1, event_type="view", film_id=3)
        
        print("\n✅ Tous les messages ont été envoyés!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\n💡 Vérifiez que:")
        print("   - Kafka est démarré: docker-compose ps kafka")
        print("   - Les topics existent: docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092")
        print("   - Vous utilisez le bon bootstrap server (localhost:9092 depuis l'hôte, kafka:29092 depuis un conteneur)")
    finally:
        if 'producer' in locals():
            producer.close()
            print("\n🔌 Producteur fermé")

if __name__ == "__main__":
    main()

