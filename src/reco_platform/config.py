"""
Configuration module - Reads environment variables for pipeline configuration.
"""

import os
from typing import Optional, List, Dict


class Config:
    """Configuration class that reads from environment variables."""
    
    # Lakehouse paths
    LAKEHOUSE_PATH: str = os.getenv("LAKEHOUSE_PATH", "/data")
    
    # Storage format
    STORAGE_FORMAT: str = os.getenv("STORAGE_FORMAT", "delta").lower()
    
    # MLflow
    MLFLOW_TRACKING_URI: str = os.getenv(
        "MLFLOW_TRACKING_URI", 
        os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    )
    
    # ALS Hyperparameters
    ALS_RANK: int = int(os.getenv("ALS_RANK", "50"))
    ALS_MAX_ITER: int = int(os.getenv("ALS_MAX_ITER", "10"))
    ALS_REG_PARAM: float = float(os.getenv("ALS_REG_PARAM", "0.1"))
    ALS_COLD_START_STRATEGY: str = os.getenv("ALS_COLD_START_STRATEGY", "drop")
    
    # Recommendation parameters
    TOP_N: int = int(os.getenv("TOP_N", "10"))
    
    # Spark configuration
    SPARK_MASTER: str = os.getenv("SPARK_MASTER", "spark://spark-master:7077")
    
    # Kafka configuration
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    
    # Data quality thresholds
    MAX_NULL_PERCENTAGE: float = float(os.getenv("MAX_NULL_PERCENTAGE", "5.0"))
    MIN_RATING: float = 0.5
    MAX_RATING: float = 5.0
    
    @classmethod
    def validate_storage_format(cls) -> None:
        """Validate that storage format is supported."""
        if cls.STORAGE_FORMAT not in ["delta", "parquet"]:
            raise ValueError(
                f"STORAGE_FORMAT must be 'delta' or 'parquet', got: {cls.STORAGE_FORMAT}"
            )
    
    @classmethod
    def get_spark_packages(cls) -> List[str]:
        """Get required Spark packages based on storage format."""
        packages = []
        if cls.STORAGE_FORMAT == "delta":
            packages.append("io.delta:delta-spark_2.12:3.0.0")
        return packages
    
    @classmethod
    def get_spark_config(cls) -> Dict[str, str]:
        """Get Spark configuration dictionary."""
        config = {
            "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension" if cls.STORAGE_FORMAT == "delta" else "",
            "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog" if cls.STORAGE_FORMAT == "delta" else "",
        }
        # Remove empty configs
        return {k: v for k, v in config.items() if v}


# Validate on import
Config.validate_storage_format()


