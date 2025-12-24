# Projet Kafka Streaming avec Spark

Ce projet permet de générer des données de streaming (clicks, views, ratings), de les envoyer à Kafka via 3 topics, et de les consommer avec Spark Streaming pour les sauvegarder dans des fichiers Parquet.

## Architecture

```
Générateur de données → Kafka (3 topics) → Spark Streaming → Fichiers Parquet
```

- **Topics Kafka**: `clicks`, `views`, `ratings`
- **Fichiers Parquet**: `data/parquet/clicks/`, `data/parquet/views/`, `data/parquet/ratings/`

> 🚀 **Démarrage rapide:** Consultez [QUICK_START.md](QUICK_START.md)  
> 📖 **Guide d'exécution détaillé:** Consultez [GUIDE_EXECUTION.md](GUIDE_EXECUTION.md)  
> 🐳 **Guide Docker:** Consultez [DOCKER_GUIDE.md](DOCKER_GUIDE.md)

## Prérequis

### Option 1: Avec Docker (Recommandé)

1. **Docker** et **Docker Compose**
   ```bash
   docker --version
   docker-compose --version
   ```

2. **Python 3.7+** (pour le producteur qui tourne localement)

### Option 2: Installation locale

1. **Java JDK 8 ou supérieur**
   ```bash
   java -version
   ```

2. **Kafka** (version 2.x ou 3.x)
   - Télécharger depuis https://kafka.apache.org/downloads
   - Extraire et démarrer Zookeeper et Kafka

3. **Apache Spark 3.x**
   - Télécharger depuis https://spark.apache.org/downloads.html

4. **Python 3.7+**

## Installation

### Option 1: Avec Docker

1. Installer les dépendances Python pour le producteur:
   ```bash
   pip install -r requirements.txt
   ```

2. Démarrer Kafka et Zookeeper avec Docker:
   ```bash
   docker-compose up -d
   ```

   Cela démarre:
   - Zookeeper (port 2181)
   - Kafka (port 9092)
   - Kafka UI (port 8080) - Interface web pour visualiser les topics

3. Vérifier que les conteneurs sont démarrés:
   ```bash
   docker-compose ps
   ```

4. Créer les topics Kafka (optionnel, auto-création activée):
   ```bash
   python create_topics.py
   ```

### Option 2: Installation locale

1. Installer les dépendances Python:
   ```bash
   pip install -r requirements.txt
   ```

2. Configurer les variables d'environnement pour Spark:
   ```bash
   # Windows
   set SPARK_HOME=C:\path\to\spark
   
   # Linux/Mac
   export SPARK_HOME=/path/to/spark
   ```

3. Démarrer Zookeeper:
   ```bash
   bin\zookeeper-server-start.bat config\zookeeper.properties
   ```

4. Démarrer Kafka:
   ```bash
   bin\kafka-server-start.bat config\server.properties
   ```

5. Créer les 3 topics:
   ```bash
   bin\kafka-topics.bat --create --topic clicks --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
   bin\kafka-topics.bat --create --topic views --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
   bin\kafka-topics.bat --create --topic ratings --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
   ```

## Utilisation

### Option 1: Avec Docker (Kafka + Spark)

1. **Démarrer Kafka et Zookeeper**:
   ```bash
   docker-compose up -d
   ```

2. **Démarrer le consumer Spark Streaming dans Docker**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer
   ```

   Ou construire et lancer séparément:
   ```bash
   docker build -f Dockerfile.spark -t spark-consumer .
   docker run --network kafka-streaming_kafka-network -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 -v ${PWD}/data:/opt/bitnami/spark/work/data -v ${PWD}/checkpoints:/opt/bitnami/spark/work/checkpoints spark-consumer
   ```

3. **Démarrer le producteur localement** (dans un autre terminal):
   ```bash
   python producer.py
   ```

### Option 2: Tout en local

1. **Démarrer le producteur** (générateur de données):
   ```bash
   python producer.py
   ```

2. **Démarrer le consumer Spark Streaming**:
   ```bash
   python consumer_spark.py
   ```

### Interface Kafka UI (avec Docker)

Si vous utilisez Docker, vous pouvez visualiser les topics et messages via l'interface web:
- URL: http://localhost:8080
- Permet de voir les topics, les messages, et les consommateurs

## Structure des données

### Clicks
- `event_type`: "click"
- `user_id`: ID de l'utilisateur (1-1000)
- `item_id`: ID de l'item (1-500)
- `timestamp`: Horodatage ISO
- `page_url`: URL de la page
- `click_duration`: Durée du clic en secondes

### Views
- `event_type`: "view"
- `user_id`: ID de l'utilisateur (1-1000)
- `item_id`: ID de l'item (1-500)
- `timestamp`: Horodatage ISO
- `view_duration`: Durée de la vue en secondes
- `device_type`: Type d'appareil (mobile/desktop/tablet)

### Ratings
- `event_type`: "rating"
- `user_id`: ID de l'utilisateur (1-1000)
- `item_id`: ID de l'item (1-500)
- `timestamp`: Horodatage ISO
- `rating`: Note (1-5)
- `review_text`: Texte de la revue

## Structure des fichiers

```
kafka_streaming/
├── producer.py                 # Générateur de données et producteur Kafka
├── consumer_spark.py           # Consumer Spark Streaming
├── create_topics.py            # Script pour créer les topics Kafka
├── requirements.txt            # Dépendances Python
├── README.md                   # Ce fichier
├── docker-compose.yml          # Configuration Docker pour Kafka/Zookeeper
├── docker-compose.spark.yml    # Extension pour Spark consumer
├── Dockerfile.spark            # Dockerfile pour Spark Streaming
├── .gitignore                  # Fichiers ignorés par Git
├── data/
│   └── parquet/
│       ├── clicks/            # Fichiers Parquet pour les clicks
│       ├── views/             # Fichiers Parquet pour les views
│       └── ratings/           # Fichiers Parquet pour les ratings
└── checkpoints/               # Checkpoints Spark Streaming
    ├── clicks/
    ├── views/
    └── ratings/
```

## Commandes Docker utiles

### Démarrer les services
```bash
docker-compose up -d
```

### Arrêter les services
```bash
docker-compose down
```

### Voir les logs
```bash
docker-compose logs -f kafka
docker-compose logs -f spark-consumer
```

### Arrêter uniquement Spark
```bash
docker-compose -f docker-compose.yml -f docker-compose.spark.yml stop spark-consumer
```

### Supprimer les données (volumes)
```bash
docker-compose down -v
```

## Notes

- Les fichiers Parquet sont sauvegardés toutes les 10 secondes (configurable dans `consumer_spark.py`)
- Les checkpoints Spark sont sauvegardés dans le dossier `checkpoints/` pour permettre la reprise après interruption
- Pour modifier la fréquence de génération des données, changez le paramètre `interval` dans `producer.py`

