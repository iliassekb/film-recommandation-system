# Spark Jobs

Ce dossier contient tous les jobs Spark du projet.

## Structure

```
spark/
└── jobs/
    ├── stream_kafka_to_silver.py      # Job de traitement streaming Kafka vers Silver
    └── stream_trending_to_gold.py    # Job de calcul des scores de trending Silver vers Gold
```

## Jobs disponibles

### stream_kafka_to_silver.py

Job Spark Structured Streaming qui :
- Lit les événements depuis Kafka (topics: `events_views`, `events_clicks`, `events_ratings`)
- Valide le schéma JSON de chaque message
- Transforme les données (timestamps, dates, filtrage)
- Écrit dans Silver avec partitionnement par `event_date`
- Gère les erreurs via Dead Letter Queue

**Utilisation :**

```bash
# Depuis la racine du projet
python spark/jobs/stream_kafka_to_silver.py

# Ou avec le fichier batch (Windows)
start_spark_consumer.bat
```

**Configuration :**

Variables d'environnement disponibles :
- `LAKEHOUSE_PATH` : Chemin du lakehouse (défaut: `lakehouse`)
- `STORAGE_FORMAT` : Format de stockage `parquet` ou `delta` (défaut: `parquet`)
- `KAFKA_BOOTSTRAP_SERVERS` : Serveurs Kafka (défaut: `localhost:9092`)
- `MIN_RATING` : Note minimale (défaut: `0.5`)
- `MAX_RATING` : Note maximale (défaut: `5.0`)

### stream_trending_to_gold.py

Job Spark Structured Streaming qui :
- Lit les événements depuis Silver (`events_views`, `events_clicks`)
- Applique des fenêtres temporelles (1h et 24h avec slide 1h)
- Agrège les événements par film dans chaque fenêtre
- Joint les vues et clics avec une jointure externe
- Calcule le score de trending : `views × 1.0 + clicks × 2.0`
- Trie les résultats par score décroissant
- Écrit dans Gold avec mode `complete` (réécriture complète)

**Utilisation :**

```bash
# Depuis la racine du projet
python spark/jobs/stream_trending_to_gold.py

# Ou avec le fichier batch (Windows)
start_trending_job.bat
```

**Configuration :**

Variables d'environnement disponibles :
- `LAKEHOUSE_PATH` : Chemin du lakehouse (défaut: `lakehouse`)
- `STORAGE_FORMAT` : Format de stockage `parquet` ou `delta` (défaut: `parquet`)

**Tables Gold générées :**
- `trending_now_1h` : Scores de trending sur fenêtres de 1 heure (disjointes)
- `trending_now_24h` : Scores de trending sur fenêtres de 24 heures (glissantes, slide 1h)

**Caractéristiques :**
- **Watermark 1h** : 2 heures (tolère les données en retard jusqu'à 2h)
- **Watermark 24h** : 26 heures (tolère les données en retard jusqu'à 26h)
- **Trigger** : Toutes les 5 secondes
- **Output Mode** : `complete` (réécrit toute la table à chaque trigger)

