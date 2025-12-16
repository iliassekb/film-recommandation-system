"""
Exemple d'utilisation de Spark avec Kafka pour le système de recommandation
Ce script montre comment lire et traiter des données depuis Kafka avec Spark
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window, count
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, TimestampType

def create_spark_session():
    """Créer une session Spark avec les configurations nécessaires"""
    spark = SparkSession.builder \
        .appName("FilmRecommendationKafkaStream") \
        .config("spark.master", "spark://spark-master:7077") \
        .config("spark.sql.warehouse.dir", "/lakehouse/warehouse") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def read_from_kafka(spark, kafka_bootstrap_servers, topic):
    """Lire un stream depuis Kafka"""
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", topic) \
        .option("startingOffsets", "latest") \
        .load()
    
    return df

def process_film_ratings(df):
    """Traiter les données de ratings de films"""
    # Schéma pour les ratings
    rating_schema = StructType([
        StructField("user_id", IntegerType(), True),
        StructField("film_id", IntegerType(), True),
        StructField("rating", FloatType(), True),
        StructField("timestamp", TimestampType(), True)
    ])
    
    # Parser les données JSON
    parsed_df = df.select(
        col("key").cast("string").alias("key"),
        from_json(col("value").cast("string"), rating_schema).alias("data"),
        col("timestamp").alias("kafka_timestamp")
    ).select("key", "data.*", "kafka_timestamp")
    
    # Agrégations par fenêtre temporelle
    windowed_df = parsed_df \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(
            window(col("timestamp"), "5 minutes"),
            col("film_id")
        ) \
        .agg(
            count("*").alias("rating_count"),
            col("rating").avg().alias("avg_rating")
        )
    
    return windowed_df

def write_to_lakehouse(df, output_path, checkpoint_path):
    """Écrire les résultats dans le lakehouse (Delta format)"""
    query = df.writeStream \
        .format("delta") \
        .outputMode("append") \
        .option("checkpointLocation", checkpoint_path) \
        .option("path", output_path) \
        .trigger(processingTime="1 minute") \
        .start()
    
    return query

def main():
    """Fonction principale"""
    # Configuration
    kafka_bootstrap_servers = "kafka:29092"
    topic = "film-ratings"
    output_path = "/lakehouse/film_ratings_aggregated"
    checkpoint_path = "/lakehouse/checkpoints/film_ratings"
    
    # Créer la session Spark
    spark = create_spark_session()
    
    print("📡 Lecture depuis Kafka...")
    kafka_df = read_from_kafka(spark, kafka_bootstrap_servers, topic)
    
    print("🔄 Traitement des données...")
    processed_df = process_film_ratings(kafka_df)
    
    print("💾 Écriture dans le lakehouse...")
    query = write_to_lakehouse(processed_df, output_path, checkpoint_path)
    
    print("✅ Stream démarré. Appuyez sur Ctrl+C pour arrêter.")
    
    try:
        query.awaitTermination()
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du stream...")
        query.stop()

if __name__ == "__main__":
    main()

