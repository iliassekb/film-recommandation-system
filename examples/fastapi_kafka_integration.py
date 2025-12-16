"""
Exemple d'intégration FastAPI avec Kafka
Ce script montre comment intégrer Kafka dans l'API FastAPI
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from kafka import KafkaProducer
import json
import logging

# Configuration
KAFKA_BOOTSTRAP_SERVERS = "kafka:29092"  # Depuis le conteneur Docker
TOPIC_RATINGS = "film-ratings"
TOPIC_EVENTS = "user-events"

# Logger
logger = logging.getLogger(__name__)

# Modèles Pydantic
class FilmRating(BaseModel):
    user_id: int
    film_id: int
    rating: float  # 0.0 à 5.0
    timestamp: Optional[str] = None

class UserEvent(BaseModel):
    user_id: int
    event_type: str  # view, click, search, etc.
    film_id: Optional[int] = None

# Créer l'application FastAPI
app = FastAPI(title="Film Recommendation API with Kafka")

# Producteur Kafka global
producer: Optional[KafkaProducer] = None

@app.on_event("startup")
async def startup_event():
    """Initialiser le producteur Kafka au démarrage"""
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8') if k else None,
            acks='all',
            retries=3
        )
        logger.info(f"✅ Connecté à Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à Kafka: {e}")
        producer = None

@app.on_event("shutdown")
async def shutdown_event():
    """Fermer le producteur Kafka à l'arrêt"""
    global producer
    if producer:
        producer.close()
        logger.info("🔌 Producteur Kafka fermé")

def send_to_kafka(topic: str, key: str, value: dict):
    """Envoyer un message à Kafka"""
    if not producer:
        logger.error("❌ Producteur Kafka non initialisé")
        return False
    
    try:
        future = producer.send(topic, key=key, value=value)
        record_metadata = future.get(timeout=10)
        logger.info(f"✅ Message envoyé à {topic} - Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'envoi à Kafka: {e}")
        return False

@app.post("/api/v1/ratings", status_code=201)
async def submit_rating(rating: FilmRating, background_tasks: BackgroundTasks):
    """
    Soumettre un rating de film
    
    Le rating est envoyé à Kafka pour traitement asynchrone
    """
    # Valider le rating
    if rating.rating < 0.0 or rating.rating > 5.0:
        raise HTTPException(status_code=400, detail="Le rating doit être entre 0.0 et 5.0")
    
    # Préparer le message
    message = rating.dict()
    if not message.get("timestamp"):
        from datetime import datetime
        message["timestamp"] = datetime.now().isoformat()
    
    # Envoyer à Kafka en arrière-plan
    background_tasks.add_task(
        send_to_kafka,
        topic=TOPIC_RATINGS,
        key=str(rating.user_id),
        value=message
    )
    
    return {
        "message": "Rating soumis avec succès",
        "rating": rating.dict()
    }

@app.post("/api/v1/events", status_code=201)
async def submit_event(event: UserEvent, background_tasks: BackgroundTasks):
    """
    Soumettre un événement utilisateur
    
    L'événement est envoyé à Kafka pour traitement
    """
    # Préparer le message
    message = event.dict()
    if not message.get("timestamp"):
        from datetime import datetime
        message["timestamp"] = datetime.now().isoformat()
    
    # Envoyer à Kafka en arrière-plan
    background_tasks.add_task(
        send_to_kafka,
        topic=TOPIC_EVENTS,
        key=str(event.user_id),
        value=message
    )
    
    return {
        "message": "Événement soumis avec succès",
        "event": event.dict()
    }

@app.get("/api/v1/kafka/status")
async def kafka_status():
    """Vérifier le statut de la connexion Kafka"""
    if producer:
        return {
            "status": "connected",
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS
        }
    else:
        return {
            "status": "disconnected",
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS
        }

@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "Film Recommendation API with Kafka Integration",
        "endpoints": {
            "submit_rating": "/api/v1/ratings",
            "submit_event": "/api/v1/events",
            "kafka_status": "/api/v1/kafka/status",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

