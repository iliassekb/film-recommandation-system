from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic_settings import BaseSettings
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import redis
import logging
import time
from recommendations_service import RecommendationsService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)


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

# Initialize Recommendations Service
recommendations_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis_client, recommendations_service
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
    
    # Initialize recommendations service
    try:
        recommendations_service = RecommendationsService(lakehouse_path=settings.lakehouse_path)
        logger.info(f"Initialized RecommendationsService with lakehouse path: {settings.lakehouse_path}")
    except Exception as e:
        logger.error(f"Failed to initialize RecommendationsService: {e}")
        recommendations_service = None
    
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

# CORS middleware (must be added before routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics middleware (after CORS)
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Middleware to track HTTP requests for Prometheus metrics"""
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response


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


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/recommendations/{user_id}")
async def get_recommendations(user_id: int, limit: int = 10):
    """
    Get film recommendations for a user
    
    Args:
        user_id: User ID
        limit: Number of recommendations to return (default: 10, max: 100)
    
    Returns:
        Dictionary with user_id and list of recommended films with details
    """
    # Validate limit
    if limit < 1:
        limit = 10
    if limit > 100:
        limit = 100
    
    # Check cache first
    cache_key = f"recommendations:user:{user_id}:limit:{limit}"
    cached_result = None
    
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                import json
                cached_result = json.loads(cached_data)
                logger.info(f"Cache hit for user {user_id}")
        except Exception as e:
            logger.warning(f"Error reading from cache: {e}")
    
    if cached_result:
        return cached_result
    
    # Check if service is available
    if recommendations_service is None:
        raise HTTPException(
            status_code=503,
            detail="Recommendations service is not available. Please check if the lakehouse data is properly loaded."
        )
    
    try:
        # Get recommendations
        recommendations = recommendations_service.get_recommendations_for_user(
            user_id=user_id,
            limit=limit,
            include_movie_details=True
        )
        
        if not recommendations:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendations found for user {user_id}. The user may not exist in the training data."
            )
        
        result = {
            "user_id": user_id,
            "count": len(recommendations),
            "recommendations": recommendations
        }
        
        # Cache the result (TTL: 1 hour)
        if redis_client:
            try:
                import json
                redis_client.setex(
                    cache_key,
                    3600,  # 1 hour TTL
                    json.dumps(result)
                )
                logger.info(f"Cached recommendations for user {user_id}")
            except Exception as e:
                logger.warning(f"Error caching result: {e}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while fetching recommendations: {str(e)}"
        )


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

