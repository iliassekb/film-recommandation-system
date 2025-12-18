# Streaming Kafka → Console

Ce script permet de capturer et afficher en temps réel les événements des 3 topics Kafka :
- `events_views` - Événements de visualisation de films
- `events_clicks` - Événements de clics utilisateurs
- `events_ratings` - Événements de notation de films

## Prérequis

1. Les services Docker doivent être démarrés :
   ```bash
   docker-compose up -d
   ```

2. Les topics Kafka doivent exister :
   ```bash
   # Vérifier les topics
   docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:29092
   
   # Si les topics n'existent pas, les créer
   python tools/kafka_topic_init.py
   # ou
   docker-compose exec kafka-topic-init python /app/tools/kafka_topic_init.py
   ```

3. Le générateur d'événements doit être en cours d'exécution (optionnel mais recommandé pour voir des données) :
   ```bash
   # Dans un terminal séparé
   docker-compose run --rm \
     -e KAFKA_BOOTSTRAP_SERVERS=kafka:29092 \
     kafka-topic-init sh -c "
       pip install --no-cache-dir kafka-python==2.0.2 && \
       python3 /app/tools/run_event_generator.py \
         --mode stream \
         --interval-ms 5
     "
   ```

## Utilisation

### Option 1 : Mode LOCAL (Recommandé pour ressources limitées)

Le mode LOCAL exécute tout sur le driver uniquement, évitant les problèmes de JARs sur les workers. **Parfait si vous avez des ressources limitées (4 cores, 2GB RAM).**

**Depuis la machine hôte (Windows/Linux/Mac):**
```bash
# Méthode simple: utiliser le script qui copie et exécute automatiquement
python3 tools/run_stream_console_from_host.py --mode local
```

**Ou manuellement:**
```bash
# 1. Copier le script dans le conteneur
docker cp tools/run_stream_console.py spark-master:/tmp/

# 2. Exécuter le script
docker-compose exec spark-master python3 /tmp/run_stream_console.py --mode local
```

### Option 2 : Mode CLUSTER (nécessite installation des JARs)

Pour utiliser le mode cluster avec les workers, vous devez d'abord installer les JARs Kafka :

**Depuis la machine hôte (Windows/Linux/Mac):**
```bash
# 1. Installer les JARs Kafka (voir scripts/install_kafka_jars.sh ou .ps1)
# 2. Lancer le streaming
python3 tools/run_stream_console_from_host.py --mode cluster
```

**Ou manuellement:**
```bash
# 1. Installer les JARs Kafka d'abord
python3 scripts/install_kafka_jars.py  # ou le script approprié

# 2. Copier et exécuter
docker cp tools/run_stream_console.py spark-master:/tmp/
docker-compose exec spark-master python3 /tmp/run_stream_console.py --mode cluster
```

## Comportement

- Le script lit depuis les 3 topics Kafka en parallèle
- Les événements sont affichés dans la console toutes les 2 secondes
- Chaque événement affiche :
  - Le topic d'origine
  - Tous les champs de l'événement (event_id, event_type, user_id, movie_id, etc.)
  - Le timestamp Kafka

## Arrêt

Appuyez sur **Ctrl+C** pour arrêter le streaming.

## Dépannage

### Erreur: `NoClassDefFoundError: Could not initialize class org.apache.spark.sql.kafka010.consumer.KafkaDataConsumer$`

**Solution:** Utilisez le mode LOCAL (Option 1 ci-dessus) qui télécharge automatiquement les JARs Kafka via `--packages`, ou installez les JARs manuellement avec `.\scripts\install_kafka_jars.ps1`

### Mode LOCAL recommandé pour ressources limitées

Si vous avez des ressources limitées (4 cores, 2GB RAM), utilisez le **mode LOCAL** qui :
- ✅ N'a pas besoin de workers Spark
- ✅ Télécharge automatiquement les JARs Kafka
- ✅ Utilise moins de ressources
- ✅ Plus simple à mettre en place

## Notes

- Le script utilise `startingOffsets: latest`, donc il ne lit que les nouveaux événements après le démarrage
- Pour lire depuis le début des topics, modifiez le script pour utiliser `startingOffsets: earliest`
- Les données sont affichées dans la console uniquement, elles ne sont pas sauvegardées
- Pour sauvegarder les données, utilisez `stream_kafka_to_silver.py` à la place
- Mode LOCAL: Utilise `local[2]` (2 threads sur le driver uniquement)
- Mode CLUSTER: Nécessite les JARs Kafka installés sur tous les workers

