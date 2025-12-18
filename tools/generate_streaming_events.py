#!/usr/bin/env python3
"""
Script de génération d'événements de streaming pour Kafka
Génère des événements views, clicks et ratings et les envoie dans les topics Kafka appropriés.
"""

import os
import json
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError


class StreamingEventGenerator:
    """Générateur d'événements de streaming pour Kafka."""
    
    def __init__(self, bootstrap_servers: str = None):
        """Initialise le générateur avec connexion Kafka."""
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", 
            "localhost:9092"
        )
        
        # Configuration du producer Kafka
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',  # Attendre confirmation de tous les replicas
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        
        # Configuration pour la génération d'événements
        self.user_ids = list(range(1, 1001))  # 1000 utilisateurs
        self.movie_ids = list(range(1, 10001))  # 10000 films
        self.device_types = ["mobile", "desktop", "tablet", "smart_tv"]
        self.click_types = ["trailer", "poster", "title", "recommendation"]
        self.ratings = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        
        # Statistiques
        self.stats = {
            "views_sent": 0,
            "clicks_sent": 0,
            "ratings_sent": 0,
            "errors": 0
        }
    
    def generate_view_event(self, user_id: Optional[int] = None, 
                           movie_id: Optional[int] = None,
                           session_id: Optional[str] = None) -> Dict[str, Any]:
        """Génère un événement de type 'view'."""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "view",
            "event_ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "user_id": user_id or random.choice(self.user_ids),
            "movie_id": movie_id or random.choice(self.movie_ids)
        }
        
        # Ajouter des champs optionnels aléatoirement
        if random.random() > 0.3:  # 70% des cas
            event["session_id"] = session_id or str(uuid.uuid4())
        
        if random.random() > 0.5:  # 50% des cas
            event["device_type"] = random.choice(self.device_types)
        
        if random.random() > 0.7:  # 30% des cas
            event["page_url"] = f"/movie/{event['movie_id']}"
        
        return event
    
    def generate_click_event(self, user_id: Optional[int] = None,
                            movie_id: Optional[int] = None,
                            session_id: Optional[str] = None) -> Dict[str, Any]:
        """Génère un événement de type 'click'."""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "click",
            "event_ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "user_id": user_id or random.choice(self.user_ids),
            "movie_id": movie_id or random.choice(self.movie_ids)
        }
        
        # Ajouter des champs optionnels
        if random.random() > 0.2:  # 80% des cas
            event["click_type"] = random.choice(self.click_types)
        
        if random.random() > 0.3:  # 70% des cas
            event["session_id"] = session_id or str(uuid.uuid4())
        
        if random.random() > 0.6:  # 40% des cas
            event["referrer"] = f"https://example.com/search?q=movie{event['movie_id']}"
        
        return event
    
    def generate_rating_event(self, user_id: Optional[int] = None,
                              movie_id: Optional[int] = None) -> Dict[str, Any]:
        """Génère un événement de type 'rating'."""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "rating",
            "event_ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "user_id": user_id or random.choice(self.user_ids),
            "movie_id": movie_id or random.choice(self.movie_ids),
            "rating": random.choice(self.ratings)
        }
        
        # Ajouter review_text aléatoirement (20% des cas)
        if random.random() > 0.8:
            reviews = [
                "Great movie!",
                "Amazing storyline",
                "Not my favorite",
                "Highly recommended",
                "Could be better",
                "Excellent acting",
                "Boring plot",
                "Must watch!",
                "Overrated",
                "Underrated gem"
            ]
            event["review_text"] = random.choice(reviews)
        
        return event
    
    def send_view_event(self, event: Dict[str, Any]) -> bool:
        """Envoie un événement view dans Kafka."""
        try:
            future = self.producer.send(
                'events_views',
                key=str(event['user_id']),  # Partition par user_id
                value=event
            )
            future.get(timeout=10)  # Attendre confirmation
            self.stats["views_sent"] += 1
            return True
        except KafkaError as e:
            print(f"❌ Erreur lors de l'envoi de l'événement view: {e}")
            self.stats["errors"] += 1
            return False
    
    def send_click_event(self, event: Dict[str, Any]) -> bool:
        """Envoie un événement click dans Kafka."""
        try:
            future = self.producer.send(
                'events_clicks',
                key=str(event['user_id']),
                value=event
            )
            future.get(timeout=10)
            self.stats["clicks_sent"] += 1
            return True
        except KafkaError as e:
            print(f"❌ Erreur lors de l'envoi de l'événement click: {e}")
            self.stats["errors"] += 1
            return False
    
    def send_rating_event(self, event: Dict[str, Any]) -> bool:
        """Envoie un événement rating dans Kafka."""
        try:
            future = self.producer.send(
                'events_ratings',
                key=str(event['user_id']),
                value=event
            )
            future.get(timeout=10)
            self.stats["ratings_sent"] += 1
            return True
        except KafkaError as e:
            print(f"❌ Erreur lors de l'envoi de l'événement rating: {e}")
            self.stats["errors"] += 1
            return False
    
    def generate_and_send_batch(self, num_events: int = 100, 
                                views_ratio: float = 0.6,
                                clicks_ratio: float = 0.3,
                                ratings_ratio: float = 0.1):
        """
        Génère et envoie un batch d'événements.
        
        Args:
            num_events: Nombre total d'événements à générer
            views_ratio: Proportion d'événements views (default: 60%)
            clicks_ratio: Proportion d'événements clicks (default: 30%)
            ratings_ratio: Proportion d'événements ratings (default: 10%)
        """
        print(f"🚀 Génération de {num_events} événements...")
        print(f"   - Views: {int(num_events * views_ratio)}")
        print(f"   - Clicks: {int(num_events * clicks_ratio)}")
        print(f"   - Ratings: {int(num_events * ratings_ratio)}")
        
        num_views = int(num_events * views_ratio)
        num_clicks = int(num_events * clicks_ratio)
        num_ratings = num_events - num_views - num_clicks
        
        # Générer des sessions pour simuler un comportement utilisateur
        sessions = {}
        
        for i in range(num_views):
            user_id = random.choice(self.user_ids)
            movie_id = random.choice(self.movie_ids)
            
            # Créer ou réutiliser une session
            if user_id not in sessions:
                sessions[user_id] = str(uuid.uuid4())
            
            view_event = self.generate_view_event(
                user_id=user_id,
                movie_id=movie_id,
                session_id=sessions[user_id]
            )
            self.send_view_event(view_event)
            
            # Simuler un click après une view (30% des cas)
            if i < num_clicks and random.random() > 0.7:
                click_event = self.generate_click_event(
                    user_id=user_id,
                    movie_id=movie_id,
                    session_id=sessions[user_id]
                )
                self.send_click_event(click_event)
            
            if (i + 1) % 10 == 0:
                print(f"   ✓ {i + 1}/{num_views} views envoyées")
        
        # Générer des clicks supplémentaires
        for i in range(num_clicks - int(num_views * 0.3)):
            user_id = random.choice(self.user_ids)
            movie_id = random.choice(self.movie_ids)
            click_event = self.generate_click_event(
                user_id=user_id,
                movie_id=movie_id
            )
            self.send_click_event(click_event)
        
        # Générer des ratings
        for i in range(num_ratings):
            user_id = random.choice(self.user_ids)
            movie_id = random.choice(self.movie_ids)
            rating_event = self.generate_rating_event(
                user_id=user_id,
                movie_id=movie_id
            )
            self.send_rating_event(rating_event)
            
            if (i + 1) % 10 == 0:
                print(f"   ✓ {i + 1}/{num_ratings} ratings envoyées")
        
        # Flush pour s'assurer que tous les messages sont envoyés
        self.producer.flush()
        print("\n✅ Batch terminé!")
        self.print_stats()
    
    def generate_continuous_stream(self, events_per_second: float = 10.0,
                                   duration_seconds: Optional[int] = None,
                                   interval_ms: float = 5.0):
        """
        Génère un stream continu d'événements.
        
        Args:
            events_per_second: Nombre d'événements par seconde (ignoré si interval_ms est défini)
            duration_seconds: Durée en secondes (None = infini)
            interval_ms: Intervalle entre événements en millisecondes (default: 5ms)
        """
        interval = interval_ms / 1000.0  # Convertir ms en secondes
        events_per_sec = 1.0 / interval
        
        print(f"🔄 Démarrage du stream continu")
        print(f"   Intervalle: {interval_ms}ms entre chaque événement")
        print(f"   Taux: ~{events_per_sec:.0f} événements/seconde")
        if duration_seconds:
            print(f"   Durée: {duration_seconds} secondes")
        else:
            print("   Durée: infinie (Ctrl+C pour arrêter)")
        print("   Affichage: chaque événement généré\n")
        
        start_time = time.time()
        event_count = 0
        
        try:
            while True:
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break
                
                # Générer un type d'événement aléatoire
                rand = random.random()
                if rand < 0.6:  # 60% views
                    event = self.generate_view_event()
                    success = self.send_view_event(event)
                    if success:
                        print(f"📺 VIEW  | user_id={event['user_id']} | movie_id={event['movie_id']} | event_id={event['event_id'][:8]}...")
                elif rand < 0.9:  # 30% clicks
                    event = self.generate_click_event()
                    success = self.send_click_event(event)
                    if success:
                        click_type = event.get('click_type', 'unknown')
                        print(f"🖱️  CLICK | user_id={event['user_id']} | movie_id={event['movie_id']} | type={click_type} | event_id={event['event_id'][:8]}...")
                else:  # 10% ratings
                    event = self.generate_rating_event()
                    success = self.send_rating_event(event)
                    if success:
                        print(f"⭐ RATING| user_id={event['user_id']} | movie_id={event['movie_id']} | rating={event['rating']} | event_id={event['event_id'][:8]}...")
                
                event_count += 1
                
                # Afficher les stats toutes les 100 événements
                if event_count % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = event_count / elapsed if elapsed > 0 else 0
                    print(f"\n📊 Stats: {event_count} événements en {elapsed:.1f}s (~{rate:.1f} evt/s)")
                    self.print_stats()
                    print()
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Arrêt du stream...")
        
        finally:
            self.producer.flush()
            print("\n✅ Stream terminé!")
            self.print_stats()
    
    def print_stats(self):
        """Affiche les statistiques d'envoi."""
        total = sum([
            self.stats["views_sent"],
            self.stats["clicks_sent"],
            self.stats["ratings_sent"]
        ])
        
        print("\n📊 Statistiques:")
        print(f"   Views:  {self.stats['views_sent']}")
        print(f"   Clicks: {self.stats['clicks_sent']}")
        print(f"   Ratings: {self.stats['ratings_sent']}")
        print(f"   Total:  {total}")
        if self.stats["errors"] > 0:
            print(f"   ❌ Erreurs: {self.stats['errors']}")
    
    def close(self):
        """Ferme la connexion Kafka."""
        self.producer.close()


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Générateur d'événements de streaming pour Kafka"
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        help="Kafka bootstrap servers (default: localhost:9092)"
    )
    parser.add_argument(
        "--mode",
        choices=["batch", "stream"],
        default="batch",
        help="Mode de génération: batch ou stream (default: batch)"
    )
    parser.add_argument(
        "--num-events",
        type=int,
        default=100,
        help="Nombre d'événements pour le mode batch (default: 100)"
    )
    parser.add_argument(
        "--events-per-second",
        type=float,
        default=10.0,
        help="Événements par seconde pour le mode stream (default: 10.0)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Durée en secondes pour le mode stream (default: infini)"
    )
    
    args = parser.parse_args()
    
    # Créer le générateur
    generator = StreamingEventGenerator(bootstrap_servers=args.bootstrap_servers)
    
    try:
        if args.mode == "batch":
            generator.generate_and_send_batch(num_events=args.num_events)
        else:
            generator.generate_continuous_stream(
                events_per_second=args.events_per_second,
                duration_seconds=args.duration
            )
    finally:
        generator.close()


if __name__ == "__main__":
    main()

