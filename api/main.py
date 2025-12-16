from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from contextlib import asynccontextmanager
import redis
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "airflow"
    postgres_password: str = "airflow"
    postgres_db: str = "airflow"
    redis_host: str = "redis"
    redis_port: int = 6379
    kafka_bootstrap_servers: str = "kafka:29092"
    mlflow_tracking_uri: str = "http://mlflow:5000"
    lakehouse_path: str = "/lakehouse"

    class Config:
        env_file = ".env"


settings = Settings()

# Initialize Redis connection
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis_client
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
    
    yield
    
    # Shutdown
    if redis_client:
        redis_client.close()
        logger.info("Disconnected from Redis")


app = FastAPI(
    title="Film Recommendation System API",
    description="API for the Big Data Film Recommendation System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Film Recommendation System API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check Redis
    try:
        if redis_client:
            redis_client.ping()
            health_status["services"]["redis"] = "connected"
        else:
            health_status["services"]["redis"] = "not_connected"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status


@app.get("/api/v1/recommendations/{user_id}")
async def get_recommendations(user_id: int, limit: int = 10):
    """
    Get film recommendations for a user
    
    Args:
        user_id: User ID
        limit: Number of recommendations to return
    
    Returns:
        List of recommended films
    """
    # TODO: Implement recommendation logic
    return {
        "user_id": user_id,
        "recommendations": [],
        "message": "Recommendation endpoint - to be implemented"
    }


@app.post("/api/v1/ratings")
async def submit_rating(user_id: int, film_id: int, rating: float):
    """
    Submit a film rating
    
    Args:
        user_id: User ID
        film_id: Film ID
        rating: Rating value (0.0 to 5.0)
    
    Returns:
        Confirmation message
    """
    # TODO: Implement rating submission logic
    # This should publish to Kafka for processing
    return {
        "message": "Rating submitted",
        "user_id": user_id,
        "film_id": film_id,
        "rating": rating
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

