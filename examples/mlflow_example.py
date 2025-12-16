"""
Exemple d'utilisation de MLflow pour tracker les expériences de recommandation
Ce script montre comment utiliser MLflow pour enregistrer des modèles et métriques
"""

import mlflow
import mlflow.sklearn
import mlflow.spark
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
import pandas as pd
import numpy as np
from datetime import datetime

# Configuration MLflow
MLFLOW_TRACKING_URI = "http://mlflow:5000"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def create_spark_session():
    """Créer une session Spark"""
    spark = SparkSession.builder \
        .appName("FilmRecommendationMLflow") \
        .config("spark.master", "spark://spark-master:7077") \
        .getOrCreate()
    
    return spark

def train_als_model(spark, ratings_df, rank=10, max_iter=10, reg_param=0.1):
    """
    Entraîner un modèle ALS (Alternating Least Squares) pour la recommandation
    
    Args:
        spark: SparkSession
        ratings_df: DataFrame Spark avec colonnes user_id, film_id, rating
        rank: Nombre de facteurs latents
        max_iter: Nombre d'itérations
        reg_param: Paramètre de régularisation
    
    Returns:
        Modèle ALS entraîné
    """
    # Diviser en train/test
    (training, test) = ratings_df.randomSplit([0.8, 0.2])
    
    # Créer et entraîner le modèle ALS
    als = ALS(
        maxIter=max_iter,
        regParam=reg_param,
        rank=rank,
        userCol="user_id",
        itemCol="film_id",
        ratingCol="rating",
        coldStartStrategy="drop"
    )
    
    model = als.fit(training)
    
    # Faire des prédictions
    predictions = model.transform(test)
    
    # Évaluer le modèle
    evaluator = RegressionEvaluator(
        metricName="rmse",
        labelCol="rating",
        predictionCol="prediction"
    )
    
    rmse = evaluator.evaluate(predictions)
    
    return model, rmse, predictions

def log_experiment_with_mlflow(spark, ratings_df, experiment_name="FilmRecommendation"):
    """
    Entraîner un modèle et logger l'expérience avec MLflow
    
    Args:
        spark: SparkSession
        ratings_df: DataFrame Spark avec les ratings
        experiment_name: Nom de l'expérience MLflow
    """
    # Créer ou récupérer l'expérience
    try:
        experiment_id = mlflow.create_experiment(experiment_name)
    except:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        experiment_id = experiment.experiment_id
    
    mlflow.set_experiment(experiment_name)
    
    # Hyperparamètres à tester
    ranks = [5, 10, 20]
    reg_params = [0.01, 0.1, 1.0]
    
    best_rmse = float('inf')
    best_model = None
    
    for rank in ranks:
        for reg_param in reg_params:
            with mlflow.start_run():
                # Entraîner le modèle
                model, rmse, predictions = train_als_model(
                    spark, ratings_df, 
                    rank=rank, 
                    reg_param=reg_param
                )
                
                # Logger les paramètres
                mlflow.log_param("rank", rank)
                mlflow.log_param("reg_param", reg_param)
                mlflow.log_param("algorithm", "ALS")
                
                # Logger les métriques
                mlflow.log_metric("rmse", rmse)
                
                # Logger le modèle Spark
                mlflow.spark.log_model(
                    model,
                    "als_model",
                    registered_model_name="FilmRecommendationALS"
                )
                
                # Logger des exemples de prédictions
                sample_predictions = predictions.select("user_id", "film_id", "rating", "prediction").limit(100)
                sample_predictions_pd = sample_predictions.toPandas()
                mlflow.log_table(sample_predictions_pd, "sample_predictions.json")
                
                # Tags
                mlflow.set_tag("model_type", "collaborative_filtering")
                mlflow.set_tag("framework", "pyspark")
                mlflow.set_tag("date", datetime.now().strftime("%Y-%m-%d"))
                
                print(f"✅ Modèle entraîné - Rank: {rank}, Reg: {reg_param}, RMSE: {rmse:.4f}")
                
                # Garder le meilleur modèle
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_model = model
    
    print(f"\n🏆 Meilleur modèle - RMSE: {best_rmse:.4f}")
    return best_model

def load_and_use_model(model_uri):
    """
    Charger un modèle depuis MLflow et l'utiliser
    
    Args:
        model_uri: URI du modèle dans MLflow (ex: "models:/FilmRecommendationALS/1")
    """
    # Charger le modèle
    model = mlflow.spark.load_model(model_uri)
    
    # Utiliser le modèle pour faire des recommandations
    # (exemple avec un DataFrame de users)
    # recommendations = model.recommendForAllUsers(10)
    
    return model

def main():
    """Fonction principale - Exemple d'utilisation"""
    print("🚀 Exemple d'utilisation de MLflow avec Spark")
    print(f"📊 MLflow Tracking URI: {MLFLOW_TRACKING_URI}")
    
    # Créer la session Spark
    spark = create_spark_session()
    
    # Charger les données depuis le lakehouse
    # ratings_df = spark.read.format("delta").load("/lakehouse/film_ratings")
    
    # Pour l'exemple, créer des données fictives
    print("📝 Création de données d'exemple...")
    data = [
        (1, 1, 4.5), (1, 2, 3.0), (1, 3, 5.0),
        (2, 1, 3.5), (2, 2, 4.0), (2, 4, 4.5),
        (3, 1, 5.0), (3, 3, 4.0), (3, 4, 3.5),
    ] * 100  # Répéter pour avoir plus de données
    
    ratings_df = spark.createDataFrame(
        data,
        ["user_id", "film_id", "rating"]
    )
    
    print(f"📊 Nombre de ratings: {ratings_df.count()}")
    
    # Entraîner et logger avec MLflow
    print("\n🔬 Démarrage de l'expérience MLflow...")
    best_model = log_experiment_with_mlflow(spark, ratings_df)
    
    print("\n✅ Expérience terminée!")
    print(f"📈 Consultez les résultats sur: {MLFLOW_TRACKING_URI}")
    
    spark.stop()

if __name__ == "__main__":
    main()

