"""
Traitement Streaming vers Silver - Job Spark Structured Streaming
Lit les événements depuis Kafka, les valide, les transforme et les stocke dans Silver.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, current_timestamp, to_timestamp, 
    date_format, lit
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    FloatType, TimestampType, DateType
)
import os
import sys
import threading
import shutil
from typing import Optional


class Config:
    """Configuration du job"""
    # Chemins
    LAKEHOUSE_PATH = os.getenv('LAKEHOUSE_PATH', 'lakehouse')
    STORAGE_FORMAT = os.getenv('STORAGE_FORMAT', 'parquet')  # 'delta' ou 'parquet'
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    # Validations
    MIN_RATING = float(os.getenv('MIN_RATING', '0.5'))
    MAX_RATING = float(os.getenv('MAX_RATING', '5.0'))
    
    # Streaming
    TRIGGER_INTERVAL = '5 seconds'
    STARTING_OFFSETS = 'latest'


class StreamKafkaToSilver:
    """Job Spark Structured Streaming pour traiter les événements Kafka vers Silver"""
    
    def __init__(self):
        self.config = Config()
        
        # Windows-specific: Set Hadoop environment variables
        if sys.platform.startswith("win"):
            hadoop_opts = os.environ.get('HADOOP_OPTS', '')
            if '-Dio.native.lib.available=false' not in hadoop_opts:
                os.environ['HADOOP_OPTS'] = hadoop_opts + ' -Dio.native.lib.available=false'
            if 'JAVA_LIBRARY_PATH' in os.environ:
                del os.environ['JAVA_LIBRARY_PATH']
        
        # Configuration Spark avec package Kafka
        spark_version = os.getenv('SPARK_VERSION', '3.5.7')
        kafka_package = f"org.apache.spark:spark-sql-kafka-0-10_2.12:{spark_version}"
        
        print(f"📦 Utilisation du package Kafka: {kafka_package}")
        print("ℹ️  Le téléchargement peut prendre quelques minutes lors de la première exécution...")
        
        builder = SparkSession.builder \
            .appName("stream_kafka_to_silver") \
            .config("spark.sql.warehouse.dir", "warehouse") \
            .config("spark.jars.packages", kafka_package)
        
        # Support Delta Lake si nécessaire
        if self.config.STORAGE_FORMAT == 'delta':
            delta_package = f"io.delta:delta-spark_2.12:{spark_version}"
            builder = builder.config("spark.jars.packages", f"{kafka_package},{delta_package}")
            print(f"📦 Ajout du package Delta Lake: {delta_package}")
        
        # Windows-specific configuration
        if sys.platform.startswith("win"):
            builder = builder.config("spark.hadoop.io.native.lib.available", "false") \
                .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2") \
                .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem") \
                .config("spark.hadoop.fs.AbstractFileSystem.file.impl", "org.apache.hadoop.fs.local.LocalFs") \
                .config("spark.hadoop.fs.file.impl.disable.cache", "true") \
                .config("spark.hadoop.fs.local.impl", "org.apache.hadoop.fs.LocalFileSystem")
        
        self.spark = builder.getOrCreate()
        
        # Additional Hadoop configuration after Spark session is created
        if sys.platform.startswith("win"):
            hadoop_conf = self.spark.sparkContext._jsc.hadoopConfiguration()
            hadoop_conf.set("io.native.lib.available", "false")
            hadoop_conf.set("fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem")
            hadoop_conf.set("fs.AbstractFileSystem.file.impl", "org.apache.hadoop.fs.local.LocalFs")
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        print(f"✅ Spark version: {self.spark.version}")
        print(f"📁 Lakehouse path: {self.config.LAKEHOUSE_PATH}")
        print(f"💾 Storage format: {self.config.STORAGE_FORMAT}")
        
        # Définir les schémas JSON pour chaque type d'événement
        self._define_schemas()
        
        # Créer les répertoires nécessaires
        self._create_directories()
    
    def _define_schemas(self):
        """Définit les schémas JSON pour chaque type d'événement"""
        
        # Schéma commun pour tous les événements
        common_fields = [
            StructField("event_id", StringType(), False),
            StructField("event_type", StringType(), False),
            StructField("event_ts", StringType(), False),
            StructField("user_id", IntegerType(), False),
            StructField("movie_id", IntegerType(), False),
        ]
        
        # Schéma pour events_views
        self.view_schema = StructType(common_fields + [
            StructField("session_id", StringType(), True),
            StructField("device_type", StringType(), True),
            StructField("page_url", StringType(), True),
        ])
        
        # Schéma pour events_clicks
        self.click_schema = StructType(common_fields + [
            StructField("click_type", StringType(), True),
            StructField("session_id", StringType(), True),
            StructField("referrer", StringType(), True),
        ])
        
        # Schéma pour events_ratings
        self.rating_schema = StructType(common_fields + [
            StructField("rating", FloatType(), False),
            StructField("review_text", StringType(), True),
        ])
    
    def _create_directories(self):
        """Crée les répertoires nécessaires pour Silver et Dead Letter Queue"""
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        
        directories = [
            os.path.join(base_path, "silver", "events_views"),
            os.path.join(base_path, "silver", "events_clicks"),
            os.path.join(base_path, "silver", "events_ratings"),
            os.path.join(base_path, "silver", "_deadletter", "events_views"),
            os.path.join(base_path, "silver", "_deadletter", "events_clicks"),
            os.path.join(base_path, "silver", "_deadletter", "events_ratings"),
            os.path.join(base_path, "_checkpoints", "stream_kafka_to_silver", "events_views"),
            os.path.join(base_path, "_checkpoints", "stream_kafka_to_silver", "events_clicks"),
            os.path.join(base_path, "_checkpoints", "stream_kafka_to_silver", "events_ratings"),
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def read_from_kafka(self, topic: str):
        """Lit les données depuis un topic Kafka"""
        return self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.config.KAFKA_BOOTSTRAP_SERVERS) \
            .option("subscribe", topic) \
            .option("startingOffsets", self.config.STARTING_OFFSETS) \
            .option("failOnDataLoss", "false") \
            .load()
    
    def process_views_stream(self):
        """Traite le stream events_views"""
        print("📥 Traitement du stream 'events_views'...")
        
        topic_name = "events_views"
        df = self.read_from_kafka(topic_name)
        
        # Parsing JSON avec validation du schéma
        parsed_df = df.select(
            col("key").cast("string"),
            col("value").cast("string"),
            col("timestamp"),
            from_json(col("value").cast("string"), self.view_schema).alias("data")
        )
        
        # Séparation Valid/Invalid
        # Valid records
        valid_df = parsed_df.filter(col("data").isNotNull()).select(
            col("data.*"),
            col("timestamp").alias("kafka_ts")
        )
        
        # Invalid records (dead letter)
        invalid_df = parsed_df.filter(col("data").isNull()).select(
            col("value").alias("raw_payload"),
            lit(topic_name).alias("topic"),
            lit("schema_validation_failed").alias("error_reason"),
            current_timestamp().alias("error_ts")
        )
        
        # Transformation des données valides
        silver_df = valid_df \
            .withColumn("event_ts", to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")) \
            .withColumn("event_date", date_format(col("event_ts"), "yyyy-MM-dd").cast(DateType())) \
            .select(
                col("event_id"),
                col("event_ts"),
                col("user_id"),
                col("movie_id"),
                col("session_id"),
                col("device_type"),
                col("event_date")
            ) \
            .filter(
                col("event_id").isNotNull() &
                col("user_id").isNotNull() &
                col("movie_id").isNotNull() &
                col("event_ts").isNotNull()
            )
        
        # Chemins
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        checkpoint_path = os.path.join(base_path, "_checkpoints", "stream_kafka_to_silver", topic_name)
        silver_path = os.path.join(base_path, "silver", topic_name)
        deadletter_path = os.path.join(base_path, "silver", "_deadletter", topic_name)
        
        # Écriture Silver
        query_valid = silver_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode("append") \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .option("checkpointLocation", checkpoint_path) \
            .partitionBy("event_date") \
            .start(silver_path)
        
        # Écriture Dead Letter Queue
        query_invalid = invalid_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode("append") \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .option("checkpointLocation", os.path.join(checkpoint_path, "deadletter")) \
            .start(deadletter_path)
        
        return query_valid, query_invalid
    
    def process_clicks_stream(self):
        """Traite le stream events_clicks"""
        print("📥 Traitement du stream 'events_clicks'...")
        
        topic_name = "events_clicks"
        df = self.read_from_kafka(topic_name)
        
        # Parsing JSON avec validation du schéma
        parsed_df = df.select(
            col("key").cast("string"),
            col("value").cast("string"),
            col("timestamp"),
            from_json(col("value").cast("string"), self.click_schema).alias("data")
        )
        
        # Séparation Valid/Invalid
        valid_df = parsed_df.filter(col("data").isNotNull()).select(
            col("data.*"),
            col("timestamp").alias("kafka_ts")
        )
        
        invalid_df = parsed_df.filter(col("data").isNull()).select(
            col("value").alias("raw_payload"),
            lit(topic_name).alias("topic"),
            lit("schema_validation_failed").alias("error_reason"),
            current_timestamp().alias("error_ts")
        )
        
        # Transformation des données valides
        silver_df = valid_df \
            .withColumn("event_ts", to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")) \
            .withColumn("event_date", date_format(col("event_ts"), "yyyy-MM-dd").cast(DateType())) \
            .select(
                col("event_id"),
                col("event_ts"),
                col("user_id"),
                col("movie_id"),
                col("click_type"),
                col("session_id"),
                col("referrer"),
                col("event_date")
            ) \
            .filter(
                col("event_id").isNotNull() &
                col("user_id").isNotNull() &
                col("movie_id").isNotNull() &
                col("event_ts").isNotNull()
            )
        
        # Chemins
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        checkpoint_path = os.path.join(base_path, "_checkpoints", "stream_kafka_to_silver", topic_name)
        silver_path = os.path.join(base_path, "silver", topic_name)
        deadletter_path = os.path.join(base_path, "silver", "_deadletter", topic_name)
        
        # Écriture Silver
        query_valid = silver_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode("append") \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .option("checkpointLocation", checkpoint_path) \
            .partitionBy("event_date") \
            .start(silver_path)
        
        # Écriture Dead Letter Queue
        query_invalid = invalid_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode("append") \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .option("checkpointLocation", os.path.join(checkpoint_path, "deadletter")) \
            .start(deadletter_path)
        
        return query_valid, query_invalid
    
    def process_ratings_stream(self):
        """Traite le stream events_ratings"""
        print("📥 Traitement du stream 'events_ratings'...")
        
        topic_name = "events_ratings"
        df = self.read_from_kafka(topic_name)
        
        # Parsing JSON avec validation du schéma
        parsed_df = df.select(
            col("key").cast("string"),
            col("value").cast("string"),
            col("timestamp"),
            from_json(col("value").cast("string"), self.rating_schema).alias("data")
        )
        
        # Séparation Valid/Invalid
        valid_df = parsed_df.filter(col("data").isNotNull()).select(
            col("data.*"),
            col("timestamp").alias("kafka_ts")
        )
        
        invalid_df = parsed_df.filter(col("data").isNull()).select(
            col("value").alias("raw_payload"),
            lit(topic_name).alias("topic"),
            lit("schema_validation_failed").alias("error_reason"),
            current_timestamp().alias("error_ts")
        )
        
        # Transformation des données valides
        silver_df = valid_df \
            .withColumn("event_ts", to_timestamp(col("event_ts"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")) \
            .withColumn("event_date", date_format(col("event_ts"), "yyyy-MM-dd").cast(DateType())) \
            .select(
                col("event_id"),
                col("event_ts"),
                col("user_id"),
                col("movie_id"),
                col("rating"),
                col("review_text"),
                col("event_date")
            ) \
            .filter(
                col("event_id").isNotNull() &
                col("user_id").isNotNull() &
                col("movie_id").isNotNull() &
                col("event_ts").isNotNull() &
                col("rating").isNotNull() &
                (col("rating") >= self.config.MIN_RATING) &
                (col("rating") <= self.config.MAX_RATING)
            )
        
        # Chemins
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        checkpoint_path = os.path.join(base_path, "_checkpoints", "stream_kafka_to_silver", topic_name)
        silver_path = os.path.join(base_path, "silver", topic_name)
        deadletter_path = os.path.join(base_path, "silver", "_deadletter", topic_name)
        
        # Écriture Silver
        query_valid = silver_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode("append") \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .option("checkpointLocation", checkpoint_path) \
            .partitionBy("event_date") \
            .start(silver_path)
        
        # Écriture Dead Letter Queue
        query_invalid = invalid_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode("append") \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .option("checkpointLocation", os.path.join(checkpoint_path, "deadletter")) \
            .start(deadletter_path)
        
        return query_valid, query_invalid
    
    def _await_stream(self, query_valid, query_invalid, stream_name):
        """Attend qu'un stream se termine"""
        try:
            query_valid.awaitTermination()
            query_invalid.awaitTermination()
        except Exception as e:
            print(f"❌ Erreur dans le stream {stream_name}: {e}")
    
    def start_all_streams(self):
        """Démarre tous les streams"""
        print("🚀 Démarrage du job stream_kafka_to_silver...")
        print("📊 Consommation des topics: events_views, events_clicks, events_ratings")
        print(f"💾 Sauvegarde dans: {self.config.LAKEHOUSE_PATH}/silver/")
        print(f"📝 Dead Letter Queue: {self.config.LAKEHOUSE_PATH}/silver/_deadletter/\n")
        
        # Démarrer les trois streams
        views_query_valid, views_query_invalid = self.process_views_stream()
        clicks_query_valid, clicks_query_invalid = self.process_clicks_stream()
        ratings_query_valid, ratings_query_invalid = self.process_ratings_stream()
        
        print("\n✅ Tous les streams sont actifs!")
        print("⏹️  Appuyez sur Ctrl+C pour arrêter\n")
        
        # Démarrer les threads pour chaque stream
        views_thread = threading.Thread(
            target=self._await_stream, 
            args=(views_query_valid, views_query_invalid, "events_views"), 
            daemon=True
        )
        clicks_thread = threading.Thread(
            target=self._await_stream, 
            args=(clicks_query_valid, clicks_query_invalid, "events_clicks"), 
            daemon=True
        )
        ratings_thread = threading.Thread(
            target=self._await_stream, 
            args=(ratings_query_valid, ratings_query_invalid, "events_ratings"), 
            daemon=True
        )
        
        views_thread.start()
        clicks_thread.start()
        ratings_thread.start()
        
        try:
            # Attendre que tous les threads se terminent (ou interruption)
            views_thread.join()
            clicks_thread.join()
            ratings_thread.join()
        except KeyboardInterrupt:
            print("\n\n⏹️  Arrêt des streams...")
            views_query_valid.stop()
            views_query_invalid.stop()
            clicks_query_valid.stop()
            clicks_query_invalid.stop()
            ratings_query_valid.stop()
            ratings_query_invalid.stop()
            print("✅ Streams arrêtés")


if __name__ == "__main__":
    job = StreamKafkaToSilver()
    job.start_all_streams()

