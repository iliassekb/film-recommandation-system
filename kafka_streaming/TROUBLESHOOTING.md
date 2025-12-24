# Guide de dépannage

## Erreur: "Failed to find data source: kafka"

Cette erreur indique que le package `spark-sql-kafka` n'est pas disponible.

### Solution 1: Utiliser le script wrapper (Recommandé)

Le fichier `consumer_spark.py` a été modifié pour inclure automatiquement le package Kafka. Lors de la première exécution, Spark téléchargera automatiquement le package (nécessite une connexion Internet).

```bash
python consumer_spark.py
```

**Note:** Le téléchargement peut prendre quelques minutes la première fois.

### Solution 2: Utiliser spark-submit avec --packages

Si vous avez `spark-submit` dans votre PATH:

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 --master local[*] consumer_spark.py
```

Ou utilisez le script wrapper:
```bash
python run_spark_consumer.py
```

### Solution 3: Installer le package manuellement

Si vous avez Spark installé localement, vous pouvez télécharger le jar et l'ajouter au classpath.

1. Téléchargez `spark-sql-kafka-0-10_2.12-3.5.0.jar` depuis Maven Central
2. Placez-le dans le dossier `jars` de votre installation Spark
3. Relancez `python consumer_spark.py`

### Solution 4: Utiliser Docker (Le plus simple)

Utilisez le container Docker qui a déjà tous les packages nécessaires:

```bash
docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer
```

## Erreur: "NoBrokersAvailable"

Kafka n'est pas accessible.

### Solutions:

1. Vérifiez que Kafka est démarré:
   ```bash
   docker-compose ps
   ```

2. Attendez 15-20 secondes après le démarrage de Kafka

3. Vérifiez que la variable d'environnement `KAFKA_BOOTSTRAP_SERVERS` est correcte:
   - Depuis la machine locale: `localhost:9092`
   - Depuis Docker: `kafka:29092`

4. Testez la connexion à Kafka:
   ```bash
   docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
   ```

## Erreur: "Topic does not exist"

Les topics n'existent pas encore.

### Solutions:

1. Créez les topics manuellement:
   ```bash
   python create_topics.py
   ```

2. Ou attendez que le producteur les crée automatiquement (auto-création activée)

3. Vérifiez dans Kafka UI: http://localhost:8080

## Spark télécharge les packages à chaque démarrage

Par défaut, Spark télécharge les packages à chaque démarrage si vous utilisez `spark.jars.packages`. 

### Solution: Cache local

Les packages sont mis en cache dans `~/.ivy2/cache` (Linux/Mac) ou `%USERPROFILE%\.ivy2\cache` (Windows). Une fois téléchargés, ils seront réutilisés.

Pour forcer l'utilisation du cache seulement, vous pouvez:
1. Télécharger le jar manuellement dans le dossier `jars` de Spark
2. Supprimer la ligne `.config("spark.jars.packages", ...)` et utiliser le jar local

## Erreur: "Unable to load native-hadoop library"

C'est un avertissement, pas une erreur. Spark utilise des implémentations Java par défaut si la bibliothèque native n'est pas disponible. Cela ne devrait pas affecter le fonctionnement.

### Pour supprimer l'avertissement:

Sur Windows, téléchargez winutils.exe et configurez `HADOOP_HOME`. Mais ce n'est pas nécessaire pour ce projet.

## Vérifier la version de Spark et Scala

Pour utiliser le bon package Kafka, vous devez connaître votre version de Spark et Scala:

```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("test").getOrCreate()
print(f"Spark version: {spark.version}")
spark.stop()
```

Puis utilisez le package correspondant:
- Spark 3.5.0 avec Scala 2.12: `org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0`
- Spark 3.4.x avec Scala 2.12: `org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.x`
- Spark 3.3.x avec Scala 2.12: `org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.x`

Si vous utilisez une autre version, modifiez la ligne dans `consumer_spark.py`:
```python
kafka_package = "org.apache.spark:spark-sql-kafka-0-10_2.12:VOTRE_VERSION"
```

