#!/usr/bin/env python3
"""
ALS Training and Recommendations Generation Job
Trains ALS model on Silver ratings, evaluates, and generates Top-N recommendations for all users.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add src to path for imports
# Try multiple paths for flexibility
src_paths = [
    os.path.join(os.path.dirname(__file__), '../../src'),
    '/opt/spark/src',
    os.path.join(os.path.dirname(__file__), '..', '..', 'src')
]
for path in src_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)
        break

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, array, struct, row_number, desc
from pyspark.sql.window import Window
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

from reco_platform.config import Config
from reco_platform.paths import (
    get_silver_path, get_gold_path, get_models_path, get_metrics_path, ensure_directory_exists
)
from reco_platform.io import read_table, write_table


def create_spark_session() -> SparkSession:
    """Create Spark session with Delta Lake support if needed."""
    builder = SparkSession.builder \
        .appName("Train_ALS_Generate_Recos") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    
    if Config.STORAGE_FORMAT == "delta":
        builder = builder \
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    
    return builder.getOrCreate()


def load_silver_ratings(spark: SparkSession) -> tuple:
    """Load ratings from Silver layer and perform time-based split."""
    print("[INFO] Loading ratings from Silver layer...")
    
    silver_ratings_path = get_silver_path("ratings")
    df = read_table(spark, silver_ratings_path)
    
    total_count = df.count()
    print(f"[INFO] Total ratings loaded: {total_count:,}")
    
    # Time-based split: last 20% of time as test set
    # Get min and max timestamps
    from pyspark.sql.functions import min as spark_min, max as spark_max
    time_stats = df.agg(
        spark_min("rating_ts").alias("min_ts"),
        spark_max("rating_ts").alias("max_ts")
    ).collect()[0]
    
    min_ts = time_stats["min_ts"]
    max_ts = time_stats["max_ts"]
    split_ts = min_ts + (max_ts - min_ts) * 0.8
    
    print(f"[INFO] Time range: {min_ts} to {max_ts}")
    print(f"[INFO] Split timestamp: {split_ts} (80% train, 20% test)")
    
    train_df = df.filter(col("rating_ts") < split_ts)
    test_df = df.filter(col("rating_ts") >= split_ts)
    
    train_count = train_df.count()
    test_count = test_df.count()
    
    print(f"[INFO] Train set: {train_count:,} ratings ({train_count/total_count*100:.1f}%)")
    print(f"[INFO] Test set: {test_count:,} ratings ({test_count/total_count*100:.1f}%)")
    
    return train_df, test_df, {
        "min_ts": str(min_ts),
        "max_ts": str(max_ts),
        "split_ts": str(split_ts),
        "train_count": train_count,
        "test_count": test_count,
        "total_count": total_count
    }


def train_als_model(spark: SparkSession, train_df) -> tuple:
    """Train ALS model on training data."""
    print("[INFO] Training ALS model...")
    print(f"[INFO] Hyperparameters:")
    print(f"  - rank: {Config.ALS_RANK}")
    print(f"  - maxIter: {Config.ALS_MAX_ITER}")
    print(f"  - regParam: {Config.ALS_REG_PARAM}")
    print(f"  - coldStartStrategy: {Config.ALS_COLD_START_STRATEGY}")
    
    als = ALS(
        rank=Config.ALS_RANK,
        maxIter=Config.ALS_MAX_ITER,
        regParam=Config.ALS_REG_PARAM,
        userCol="user_id",
        itemCol="movie_id",
        ratingCol="rating",
        coldStartStrategy=Config.ALS_COLD_START_STRATEGY,
        implicitPrefs=False
    )
    
    model = als.fit(train_df)
    
    print("[INFO] ALS model training completed!")
    
    return model


from pyspark.sql import functions as F

def evaluate_model(model, test_df) -> dict:
    """Evaluate ALS model on test set."""
    print("[INFO] Evaluating model on test set...")

    predictions = model.transform(test_df)

    # Filter out null/NaN predictions (cold start)
    pred = F.col("prediction")
    predictions = predictions.filter(pred.isNotNull() & (~F.isnan(pred)))

    evaluator = RegressionEvaluator(
        metricName="rmse",
        labelCol="rating",
        predictionCol="prediction"
    )

    rmse = evaluator.evaluate(predictions)

    eval_count = predictions.count()
    test_count = test_df.count()

    print(f"[INFO] Evaluation results:")
    print(f"  - Test set size: {test_count:,}")
    print(f"  - Predictions made: {eval_count:,}")
    print(f"  - RMSE: {rmse:.4f}")

    return {
        "rmse": float(rmse),
        "test_count": test_count,
        "predictions_count": eval_count,
        "coverage": float(eval_count / test_count) if test_count > 0 else 0.0
    }



def generate_recommendations(spark: SparkSession, model, train_df) -> tuple:
    """Generate Top-N recommendations for all users."""
    print(f"[INFO] Generating Top-{Config.TOP_N} recommendations for all users...")
    
    # Get all unique users from training data
    users_df = train_df.select("user_id").distinct()
    user_count = users_df.count()
    print(f"[INFO] Generating recommendations for {user_count:,} users...")
    
    # Generate recommendations
    recommendations = model.recommendForUserSubset(users_df, Config.TOP_N)
    
    # Transform to desired schema:
    # user_id, recommendations (array<struct<movie_id:int, score:float, rank:int>>)
    from pyspark.sql.functions import explode, monotonically_increasing_id
    
    # Explode recommendations array
    recs_exploded = recommendations.select(
        col("user_id"),
        explode(col("recommendations")).alias("rec")
    ).select(
        col("user_id"),
        col("rec.movie_id").alias("movie_id"),
        col("rec.rating").alias("score")
    )
    
    # Add rank within each user
    window = Window.partitionBy("user_id").orderBy(desc("score"))
    recs_with_rank = recs_exploded.withColumn("rank", row_number().over(window))
    
    # Group back into array
    from pyspark.sql.functions import collect_list
    recs_final = recs_with_rank.groupBy("user_id").agg(
        collect_list(
            struct(
                col("movie_id"),
                col("score"),
                col("rank")
            )
        ).alias("recommendations")
    )
    
    # Add metadata columns
    model_version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    recs_final = recs_final.withColumn("model_version", lit(model_version))
    recs_final = recs_final.withColumn("generated_ts", lit(datetime.utcnow()).cast("timestamp"))
    
    rec_count = recs_final.count()
    print(f"[INFO] Generated recommendations for {rec_count:,} users")
    
    return recs_final, model_version


def save_model(model, model_version: str) -> str:
    """Save trained model to Gold layer."""
    model_path = get_models_path("als", model_version)
    ensure_directory_exists(model_path)
    
    print(f"[INFO] Saving model to {model_path}")
    model.write().overwrite().save(model_path)
    
    return model_path


def save_metrics(eval_results: dict, split_info: dict, model_version: str) -> str:
    """Save training metrics to JSON file."""
    metrics_dir = get_metrics_path()
    ensure_directory_exists(metrics_dir)
    
    metrics_path = os.path.join(metrics_dir, f"run_metrics_{model_version}.json")
    
    metrics_data = {
        "model_version": model_version,
        "execution_ts": datetime.utcnow().isoformat() + "Z",
        "hyperparameters": {
            "rank": Config.ALS_RANK,
            "max_iter": Config.ALS_MAX_ITER,
            "reg_param": Config.ALS_REG_PARAM,
            "cold_start_strategy": Config.ALS_COLD_START_STRATEGY
        },
        "dataset_info": {
            "storage_format": Config.STORAGE_FORMAT,
            "split_info": split_info
        },
        "evaluation": eval_results,
        "recommendations": {
            "top_n": Config.TOP_N
        }
    }
    
    with open(metrics_path, 'w') as f:
        json.dump(metrics_data, f, indent=2)
    
    print(f"[INFO] Metrics saved to {metrics_path}")
    return metrics_path


def log_to_mlflow(eval_results: dict, split_info: dict, model_version: str, model_path: str) -> bool:
    """Log experiment to MLflow."""
    try:
        import mlflow
        import mlflow.spark
        
        print(f"[INFO] Logging to MLflow: {Config.MLFLOW_TRACKING_URI}")
        
        mlflow.set_tracking_uri(Config.MLFLOW_TRACKING_URI)
        
        with mlflow.start_run(run_name=f"als_training_{model_version}"):
            # Log parameters
            mlflow.log_param("rank", Config.ALS_RANK)
            mlflow.log_param("max_iter", Config.ALS_MAX_ITER)
            mlflow.log_param("reg_param", Config.ALS_REG_PARAM)
            mlflow.log_param("cold_start_strategy", Config.ALS_COLD_START_STRATEGY)
            mlflow.log_param("top_n", Config.TOP_N)
            mlflow.log_param("storage_format", Config.STORAGE_FORMAT)
            
            # Log metrics
            mlflow.log_metric("rmse", eval_results["rmse"])
            mlflow.log_metric("test_count", eval_results["test_count"])
            mlflow.log_metric("predictions_count", eval_results["predictions_count"])
            mlflow.log_metric("coverage", eval_results["coverage"])
            mlflow.log_metric("train_count", split_info["train_count"])
            
            # Log model (save model first, then log the path)
            # Note: We need to use the model object directly, not load from path
            # For Spark ML models, we log the model path as artifact
            mlflow.log_artifact(model_path, artifact_path="als_model")
            
            # Log metrics JSON as artifact
            metrics_path = save_metrics(eval_results, split_info, model_version)
            mlflow.log_artifact(metrics_path)
        
        print("[INFO] Successfully logged to MLflow")
        return True
        
    except ImportError:
        print("[WARN] MLflow not available (missing dependencies), skipping MLflow logging")
        return False
    except Exception as e:
        print(f"[WARN] MLflow logging failed: {e}, continuing without MLflow")
        return False


def main():
    """Main training and recommendations function."""
    print("=" * 80)
    print("ALS Training and Recommendations Generation")
    print("=" * 80)
    print(f"[INFO] Lakehouse path: {Config.LAKEHOUSE_PATH}")
    print(f"[INFO] Storage format: {Config.STORAGE_FORMAT}")
    print(f"[INFO] MLflow URI: {Config.MLFLOW_TRACKING_URI}")
    print()
    
    spark = create_spark_session()
    
    try:
        # Load and split data
        train_df, test_df, split_info = load_silver_ratings(spark)
        
        # Train model
        model = train_als_model(spark, train_df)
        
        # Evaluate
        eval_results = evaluate_model(model, test_df)
        
        # Generate recommendations
        recs_df, model_version = generate_recommendations(spark, model, train_df)
        
        # Save model
        model_path = save_model(model, model_version)
        
        # Save metrics
        metrics_path = save_metrics(eval_results, split_info, model_version)
        
        # Log to MLflow (optional, continues on failure)
        mlflow_success = log_to_mlflow(eval_results, split_info, model_version, model_path)
        
        # Write recommendations to Gold
        gold_recs_path = get_gold_path("recommendations_als")
        print(f"[INFO] Writing recommendations to {gold_recs_path}")
        write_table(recs_df, gold_recs_path, mode="overwrite")
        
        print()
        print("=" * 80)
        print("[SUCCESS] ALS training and recommendations generation completed!")
        print("=" * 80)
        print(f"Model version: {model_version}")
        print(f"Model path: {model_path}")
        print(f"Recommendations path: {gold_recs_path}")
        print(f"Recommendations count: {recs_df.count():,}")
        print(f"RMSE: {eval_results['rmse']:.4f}")
        print(f"MLflow logged: {mlflow_success}")
        
    except Exception as e:
        print(f"[ERROR] Training job failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

