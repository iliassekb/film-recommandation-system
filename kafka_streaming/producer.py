"""
Générateur de données de streaming (events_views, events_clicks, events_ratings) et producteur Kafka
Génère des événements selon le schéma Silver avec event_id, event_type, event_ts, etc.
"""
import json
import time
import random
import os
import uuid
from datetime import datetime, timezone
from kafka import KafkaProducer
from typing import Dict, Any

class StreamDataGenerator:
    """Générateur de données de streaming selon le schéma Silver"""
    
    def __init__(self):
        # Utiliser variable d'environnement ou localhost par défaut
        kafka_broker = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_broker],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    
    def _generate_event_ts(self) -> str:
        """Génère un timestamp ISO-8601 avec millisecondes"""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    def generate_click(self) -> Dict[str, Any]:
        """Génère un événement de clic selon le schéma events_clicks"""
        return {
            'event_id': str(uuid.uuid4()),
            'event_type': 'click',
            'event_ts': self._generate_event_ts(),
            'user_id': random.randint(1, 1000),
            'movie_id': random.randint(1, 500),
            'click_type': random.choice(['trailer', 'poster', 'title', 'recommendation']),
            'session_id': str(uuid.uuid4()),
            'referrer': f'https://example.com/page/{random.randint(1, 50)}'
        }
    
    def generate_view(self) -> Dict[str, Any]:
        """Génère un événement de vue selon le schéma events_views"""
        return {
            'event_id': str(uuid.uuid4()),
            'event_type': 'view',
            'event_ts': self._generate_event_ts(),
            'user_id': random.randint(1, 1000),
            'movie_id': random.randint(1, 500),
            'session_id': str(uuid.uuid4()),
            'device_type': random.choice(['mobile', 'desktop', 'tablet']),
            'page_url': f'/movie/{random.randint(1, 500)}'
        }
    
    def generate_rating(self) -> Dict[str, Any]:
        """Génère un événement de notation selon le schéma events_ratings"""
        # Rating doit être un multiple de 0.5 entre 0.5 et 5.0
        rating = round(random.uniform(0.5, 5.0) * 2) / 2
        
        return {
            'event_id': str(uuid.uuid4()),
            'event_type': 'rating',
            'event_ts': self._generate_event_ts(),
            'user_id': random.randint(1, 1000),
            'movie_id': random.randint(1, 500),
            'rating': rating,
            'review_text': f'Review text {random.randint(1, 100)}' if random.random() > 0.3 else None
        }
    
    def send_to_kafka(self, topic: str, data: Dict[str, Any]):
        """Envoie les données à Kafka"""
        try:
            self.producer.send(topic, data)
            print(f"✅ Données envoyées au topic {topic}: {data['event_type']} (event_id: {data['event_id'][:8]}...)")
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi: {e}")
    
    def start_streaming(self, interval: float = 1.0):
        """Démarre la génération et l'envoi de données en streaming"""
        print("🚀 Démarrage du générateur de streaming...")
        print("📊 Envoi de données aux topics: events_views, events_clicks, events_ratings")
        print("⏹️  Appuyez sur Ctrl+C pour arrêter\n")
        
        try:
            while True:
                # Génère et envoie un clic
                click_data = self.generate_click()
                self.send_to_kafka('events_clicks', click_data)
                
                time.sleep(interval)
                
                # Génère et envoie une vue
                view_data = self.generate_view()
                self.send_to_kafka('events_views', view_data)
                
                time.sleep(interval)
                
                # Génère et envoie une notation
                rating_data = self.generate_rating()
                self.send_to_kafka('events_ratings', rating_data)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Arrêt du générateur...")
        finally:
            self.producer.close()
            print("✅ Générateur arrêté")

if __name__ == "__main__":
    generator = StreamDataGenerator()
    generator.start_streaming(interval=0.5)  # Génère des données toutes les 0.5 secondes

