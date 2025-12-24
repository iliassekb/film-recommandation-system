"""
Traitement Streaming Silver vers Gold - Job Spark Structured Streaming
Lit les événements depuis Silver, calcule des agrégations temporelles et génère des scores de trending.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, window, count, coalesce, lit, sum as spark_sum
)
import os
import sys
import threading


class Config:
    """Configuration du job"""
    # Chemins
    LAKEHOUSE_PATH = os.getenv('LAKEHOUSE_PATH', 'lakehouse')
    STORAGE_FORMAT = os.getenv('STORAGE_FORMAT', 'parquet')  # 'parquet' ou 'delta'
    
    # Streaming
    TRIGGER_INTERVAL = '5 seconds'
    
    # Watermarks
    WATERMARK_1H = '2 hours'
    WATERMARK_24H = '26 hours'


class StreamTrendingToGold:
    """Job Spark Structured Streaming pour calculer les scores de trending depuis Silver"""
    
    def __init__(self):
        self.config = Config()
        
        # Windows-specific: Set Hadoop environment variables
        if sys.platform.startswith("win"):
            hadoop_opts = os.environ.get('HADOOP_OPTS', '')
            if '-Dio.native.lib.available=false' not in hadoop_opts:
                os.environ['HADOOP_OPTS'] = hadoop_opts + ' -Dio.native.lib.available=false'
            if 'JAVA_LIBRARY_PATH' in os.environ:
                del os.environ['JAVA_LIBRARY_PATH']
        
        # Configuration Spark
        builder = SparkSession.builder \
            .appName("stream_trending_to_gold") \
            .config("spark.sql.warehouse.dir", "warehouse") \
            .config("spark.sql.streaming.schemaInference", "true")
        
        # Support Delta Lake si nécessaire
        if self.config.STORAGE_FORMAT == 'delta':
            spark_version = os.getenv('SPARK_VERSION', '3.5.7')
            delta_version = os.getenv('DELTA_VERSION', '3.0.0')
            delta_package = f"io.delta:delta-spark_2.12:{delta_version}"
            builder = builder.config("spark.jars.packages", delta_package) \
                .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
                .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            print(f"📦 Ajout du package Delta Lake: {delta_package}")
            print("⚙️  Configuration Delta Lake: extensions et catalog activés")
        else:
            print("📦 Utilisation du format Parquet")
        
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
        
        # Créer les répertoires nécessaires
        self._create_directories()
    
    def _create_directories(self):
        """Crée les répertoires nécessaires pour Gold et checkpoints"""
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        
        directories = [
            os.path.join(base_path, "gold", "trending_now_1h"),
            os.path.join(base_path, "gold", "trending_now_24h"),
            os.path.join(base_path, "_checkpoints", "stream_trending_to_gold", "trending_1h"),
            os.path.join(base_path, "_checkpoints", "stream_trending_to_gold", "trending_24h"),
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_silver_path(self, table_name: str) -> str:
        """Retourne le chemin complet vers une table Silver"""
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        return os.path.join(base_path, "silver", table_name)
    
    def get_gold_path(self, table_name: str) -> str:
        """Retourne le chemin complet vers une table Gold"""
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        return os.path.join(base_path, "gold", table_name)
    
    def get_checkpoint_path(self, stream_name: str) -> str:
        """Retourne le chemin complet vers un checkpoint"""
        base_path = os.path.abspath(self.config.LAKEHOUSE_PATH)
        return os.path.join(base_path, "_checkpoints", "stream_trending_to_gold", stream_name)
    
    def read_silver_stream(self, table_name: str):
        """Lit une table Silver en streaming"""
        silver_path = self.get_silver_path(table_name)
        print(f"📖 Lecture streaming depuis: {silver_path}")
        
        return self.spark \
            .readStream \
            .format(self.config.STORAGE_FORMAT) \
            .load(silver_path)
    
    def aggregate_views_1h(self, views_df):
        """Agrège les vues sur une fenêtre de 1 heure"""
        print("📊 Agrégation des vues - Fenêtre 1h...")
        
        views_agg = views_df \
            .withWatermark("event_ts", self.config.WATERMARK_1H) \
            .groupBy(
                window(col("event_ts"), "1 hour"),
                col("movie_id")
            ) \
            .agg(
                count("*").alias("views")
            ) \
            .select(
                col("window.end").alias("window_end"),
                col("movie_id"),
                col("views")
            )
        
        return views_agg
    
    def aggregate_clicks_1h(self, clicks_df):
        """Agrège les clics sur une fenêtre de 1 heure"""
        print("📊 Agrégation des clics - Fenêtre 1h...")
        
        clicks_agg = clicks_df \
            .withWatermark("event_ts", self.config.WATERMARK_1H) \
            .groupBy(
                window(col("event_ts"), "1 hour"),
                col("movie_id")
            ) \
            .agg(
                count("*").alias("clicks")
            ) \
            .select(
                col("window.end").alias("window_end"),
                col("movie_id"),
                col("clicks")
            )
        
        return clicks_agg
    
    def aggregate_views_24h(self, views_df):
        """Agrège les vues sur une fenêtre de 24 heures (glissante, slide 1h)"""
        print("📊 Agrégation des vues - Fenêtre 24h (slide 1h)...")
        
        views_agg = views_df \
            .withWatermark("event_ts", self.config.WATERMARK_24H) \
            .groupBy(
                window(col("event_ts"), "24 hours", "1 hour"),  # 24h window, slide 1h
                col("movie_id")
            ) \
            .agg(
                count("*").alias("views")
            ) \
            .select(
                col("window.end").alias("window_end"),
                col("movie_id"),
                col("views")
            )
        
        return views_agg
    
    def aggregate_clicks_24h(self, clicks_df):
        """Agrège les clics sur une fenêtre de 24 heures (glissante, slide 1h)"""
        print("📊 Agrégation des clics - Fenêtre 24h (slide 1h)...")
        
        clicks_agg = clicks_df \
            .withWatermark("event_ts", self.config.WATERMARK_24H) \
            .groupBy(
                window(col("event_ts"), "24 hours", "1 hour"),  # 24h window, slide 1h
                col("movie_id")
            ) \
            .agg(
                count("*").alias("clicks")
            ) \
            .select(
                col("window.end").alias("window_end"),
                col("movie_id"),
                col("clicks")
            )
        
        return clicks_agg
    
    def calculate_trending_score(self, views_agg, clicks_agg):
        """Fusionne les agrégations et calcule le score de trending"""
        print("🔗 Fusion et calcul du score de trending...")
        
        # Pour les jointures stream-stream, Spark nécessite un watermark dans les clés
        # On utilise une union suivie d'une agrégation pour éviter ce problème
        
        # Ajouter les colonnes manquantes pour l'union
        views_unified = views_agg \
            .withColumn("views", col("views").cast("long")) \
            .withColumn("clicks", lit(0).cast("long"))
        
        clicks_unified = clicks_agg \
            .withColumn("views", lit(0).cast("long")) \
            .withColumn("clicks", col("clicks").cast("long"))
        
        # Union des deux streams
        combined_df = views_unified.unionByName(clicks_unified, allowMissingColumns=True)
        
        # Agrégation finale par window_end et movie_id avec watermark
        # Note: orderBy n'est pas supporté en streaming (sauf en mode complete)
        trending_df = combined_df \
            .withWatermark("window_end", "1 hour") \
            .groupBy("window_end", "movie_id") \
            .agg(
                spark_sum("views").alias("views"),
                spark_sum("clicks").alias("clicks")
            ) \
            .select(
                col("window_end").alias("window_ts"),
                col("movie_id"),
                col("views"),
                col("clicks"),
                (col("views") * 1.0 + col("clicks") * 2.0).alias("trend_score")
            )
        
        return trending_df
    
    def process_trending_1h(self):
        """Traite les tendances sur une fenêtre de 1 heure"""
        print("📥 Traitement du trending 1h...")
        
        # Lecture depuis Silver
        views_df = self.read_silver_stream("events_views")
        clicks_df = self.read_silver_stream("events_clicks")
        
        # Agrégation
        views_agg = self.aggregate_views_1h(views_df)
        clicks_agg = self.aggregate_clicks_1h(clicks_df)
        
        # Calcul du score de trending
        trending_df = self.calculate_trending_score(views_agg, clicks_agg)
        
        # Chemins
        gold_path = self.get_gold_path("trending_now_1h")
        checkpoint_path = self.get_checkpoint_path("trending_1h")
        
        print(f"💾 Écriture dans Gold: {gold_path}")
        print(f"📝 Checkpoint: {checkpoint_path}")
        
        # Écriture : mode 'complete' pour Delta, 'append' pour Parquet
        # Note: Parquet ne supporte que 'append' en streaming
        output_mode = "complete" if self.config.STORAGE_FORMAT == "delta" else "append"
        
        query = trending_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode(output_mode) \
            .option("checkpointLocation", checkpoint_path) \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .start(gold_path)
        
        return query
    
    def process_trending_24h(self):
        """Traite les tendances sur une fenêtre de 24 heures (glissante)"""
        print("📥 Traitement du trending 24h...")
        
        # Lecture depuis Silver
        views_df = self.read_silver_stream("events_views")
        clicks_df = self.read_silver_stream("events_clicks")
        
        # Agrégation
        views_agg = self.aggregate_views_24h(views_df)
        clicks_agg = self.aggregate_clicks_24h(clicks_df)
        
        # Calcul du score de trending
        trending_df = self.calculate_trending_score(views_agg, clicks_agg)
        
        # Chemins
        gold_path = self.get_gold_path("trending_now_24h")
        checkpoint_path = self.get_checkpoint_path("trending_24h")
        
        print(f"💾 Écriture dans Gold: {gold_path}")
        print(f"📝 Checkpoint: {checkpoint_path}")
        
        # Écriture : mode 'complete' pour Delta, 'append' pour Parquet
        # Note: Parquet ne supporte que 'append' en streaming
        output_mode = "complete" if self.config.STORAGE_FORMAT == "delta" else "append"
        
        query = trending_df.writeStream \
            .format(self.config.STORAGE_FORMAT) \
            .outputMode(output_mode) \
            .option("checkpointLocation", checkpoint_path) \
            .trigger(processingTime=self.config.TRIGGER_INTERVAL) \
            .start(gold_path)
        
        return query
    
    def _await_stream(self, query, stream_name):
        """Attend qu'un stream se termine"""
        try:
            query.awaitTermination()
        except Exception as e:
            print(f"❌ Erreur dans le stream {stream_name}: {e}")
    
    def start_all_streams(self):
        """Démarre tous les streams de trending"""
        print("🚀 Démarrage du job stream_trending_to_gold...")
        print("📊 Calcul des scores de trending:")
        print("   - trending_now_1h (fenêtre 1h)")
        print("   - trending_now_24h (fenêtre 24h, slide 1h)")
        print(f"💾 Sauvegarde dans: {self.config.LAKEHOUSE_PATH}/gold/\n")
        
        # Démarrer les deux streams
        query_1h = self.process_trending_1h()
        query_24h = self.process_trending_24h()
        
        print("\n✅ Tous les streams sont actifs!")
        print("⏹️  Appuyez sur Ctrl+C pour arrêter\n")
        
        # Démarrer les threads pour chaque stream
        thread_1h = threading.Thread(
            target=self._await_stream, 
            args=(query_1h, "trending_1h"), 
            daemon=True
        )
        thread_24h = threading.Thread(
            target=self._await_stream, 
            args=(query_24h, "trending_24h"), 
            daemon=True
        )
        
        thread_1h.start()
        thread_24h.start()
        
        try:
            # Attendre que tous les threads se terminent (ou interruption)
            thread_1h.join()
            thread_24h.join()
        except KeyboardInterrupt:
            print("\n\n⏹️  Arrêt des streams...")
            query_1h.stop()
            query_24h.stop()
            print("✅ Streams arrêtés")


if __name__ == "__main__":
    job = StreamTrendingToGold()
    job.start_all_streams()

