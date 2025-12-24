# Guide d'exécution - Kafka Streaming avec Spark

Ce guide vous explique comment exécuter le projet étape par étape.

## 📋 Prérequis

Avant de commencer, assurez-vous d'avoir:

- ✅ **Docker** et **Docker Compose** installés
- ✅ **Python 3.7+** installé
- ✅ **pip** installé

Vérifiez vos installations:
```bash
docker --version
docker-compose --version
python --version
pip --version
```

## 🚀 Exécution complète avec Docker

### Étape 1: Installation des dépendances Python

Installez les packages Python nécessaires pour le producteur:

```bash
pip install -r requirements.txt
```

### Étape 2: Démarrer Kafka et Zookeeper

Dans un premier terminal, démarrez les services Kafka:

```bash
docker-compose up -d
```

Ou sur Windows, double-cliquez sur `start_docker.bat`

**Vérification:**
```bash
docker-compose ps
```

Vous devriez voir:
- `zookeeper` (port 2181)
- `kafka` (port 9092)
- `kafka-ui` (port 8080)

**Attendre quelques secondes** que Kafka soit complètement démarré (environ 10-15 secondes).

### Étape 3: Créer les topics Kafka (Optionnel)

Les topics sont créés automatiquement, mais vous pouvez les créer manuellement:

```bash
python create_topics.py
```

Ou sur Windows, double-cliquez sur `setup_topics.bat`

Vous devriez voir:
```
✅ Topics créés avec succès:
   - clicks
   - views
   - ratings
```

### Étape 4: Démarrer le générateur de données (Producteur)

Dans un **nouveau terminal**, démarrez le producteur:

```bash
python producer.py
```

Ou sur Windows, double-cliquez sur `start_producer.bat`

Vous devriez voir:
```
🚀 Démarrage du générateur de streaming...
📊 Envoi de données aux topics: clicks, views, ratings
⏹️  Appuyez sur Ctrl+C pour arrêter

✅ Données envoyées au topic clicks: click
✅ Données envoyées au topic views: view
✅ Données envoyées au topic ratings: rating
...
```

**Laissez ce terminal ouvert** - il envoie continuellement des données à Kafka.

### Étape 5: Démarrer le consumer Spark Streaming

Dans un **troisième terminal**, démarrez le consumer Spark:

**Option A: Avec Docker (Recommandé)**
```bash
docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer
```

Ou sur Windows, double-cliquez sur `start_spark_docker.bat`

**Option B: En local (si vous avez Spark installé)**
```bash
python consumer_spark.py
```

Ou sur Windows, double-cliquez sur `start_consumer.bat`

Vous devriez voir:
```
🚀 Démarrage du consumer Spark Streaming...
📊 Consommation des topics: clicks, views, ratings
💾 Sauvegarde dans: data/parquet/

📥 Traitement du stream 'clicks'...
📥 Traitement du stream 'views'...
📥 Traitement du stream 'ratings'...

✅ Tous les streams sont actifs!
⏹️  Appuyez sur Ctrl+C pour arrêter
```

### Étape 6: Vérifier que tout fonctionne

#### A. Vérifier dans Kafka UI

Ouvrez votre navigateur sur: **http://localhost:8080**

Vous pouvez:
- Voir les 3 topics: `clicks`, `views`, `ratings`
- Voir les messages qui arrivent en temps réel
- Voir les consommateurs actifs

#### B. Vérifier les fichiers Parquet

Les fichiers Parquet sont créés toutes les 10 secondes dans:
```
data/parquet/clicks/
data/parquet/views/
data/parquet/ratings/
```

Après quelques minutes, vous devriez voir des fichiers `.parquet` apparaître.

Pour vérifier (sur Windows PowerShell):
```powershell
Get-ChildItem -Recurse data/parquet/ | Select-Object Name, Length, LastWriteTime
```

#### C. Vérifier les logs

**Logs Kafka:**
```bash
docker-compose logs -f kafka
```

**Logs Spark Consumer:**
```bash
docker-compose logs -f spark-consumer
```

## 📊 Ordre d'exécution recommandé

```
1. Terminal 1: docker-compose up -d           (Kafka/Zookeeper)
   ↓ Attendre 10-15 secondes
   
2. Terminal 2: python producer.py            (Générateur de données)
   ↓ Laissez tourner
   
3. Terminal 3: docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer
   ↓ (Spark Consumer - lit depuis Kafka et sauvegarde en Parquet)
```

## ⏹️ Arrêter l'application

### Arrêter le producteur
Dans le terminal du producteur, appuyez sur: `Ctrl+C`

### Arrêter le consumer Spark
Dans le terminal du consumer, appuyez sur: `Ctrl+C`

### Arrêter Kafka
```bash
docker-compose down
```

Ou pour arrêter tout:
```bash
docker-compose -f docker-compose.yml -f docker-compose.spark.yml down
```

## 🔄 Redémarrer après arrêt

1. Redémarrer Kafka:
   ```bash
   docker-compose up -d
   ```

2. Redémarrer le producteur:
   ```bash
   python producer.py
   ```

3. Redémarrer le consumer Spark:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer
   ```

**Note:** Les fichiers Parquet existants ne seront pas écrasés, les nouvelles données seront ajoutées.

## 🐛 Dépannage

### Problème: Kafka ne démarre pas

**Solution:**
1. Vérifiez que les ports 9092, 2181, 8080 ne sont pas utilisés
2. Arrêtez tous les containers: `docker-compose down`
3. Redémarrez: `docker-compose up -d`
4. Attendez 15-20 secondes que Kafka soit complètement démarré

### Problème: Le producteur ne peut pas se connecter à Kafka

**Erreur typique:** `NoBrokersAvailable`

**Solution:**
1. Vérifiez que Kafka est démarré: `docker-compose ps`
2. Attendez quelques secondes de plus
3. Vérifiez les logs: `docker-compose logs kafka`

### Problème: "Failed to find data source: kafka"

**Solution:**
1. Le package Kafka sera téléchargé automatiquement lors de la première exécution
2. Assurez-vous d'avoir une connexion Internet
3. Le téléchargement peut prendre quelques minutes la première fois
4. Pour forcer une version spécifique de Spark, définissez la variable d'environnement:
   ```bash
   set SPARK_VERSION=3.5.0  # Windows
   export SPARK_VERSION=3.5.0  # Linux/Mac
   ```
5. Voir `TROUBLESHOOTING.md` pour plus de détails

### Problème: Spark ne peut pas se connecter à Kafka

**Solution:**
1. Vérifiez que Kafka est démarré: `docker-compose ps`
2. Vérifiez que les deux containers sont sur le même réseau
3. Vérifiez les logs Spark: `docker-compose logs spark-consumer`
4. Assurez-vous que la variable d'environnement `KAFKA_BOOTSTRAP_SERVERS=kafka:29092` est bien définie

### Problème: Aucun fichier Parquet n'est créé

**Solution:**
1. Vérifiez que le producteur envoie bien des données (regardez les logs)
2. Vérifiez dans Kafka UI que les messages arrivent bien dans les topics
3. Attendez au moins 10 secondes (les fichiers sont créés toutes les 10 secondes)
4. Vérifiez les permissions des dossiers `data/` et `checkpoints/`
5. Vérifiez les logs Spark pour voir s'il y a des erreurs

### Problème: "Topic does not exist"

**Solution:**
1. Créez les topics manuellement: `python create_topics.py`
2. Ou attendez que le producteur les crée automatiquement (auto-création activée)

## 📈 Monitoring et visualisation

### Kafka UI
Accédez à http://localhost:8080 pour:
- Voir tous les topics
- Voir les messages en temps réel
- Voir les métriques des topics
- Voir les consommateurs actifs

### Vérifier les messages Kafka via ligne de commande

**Voir les messages du topic clicks:**
```bash
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic clicks --from-beginning
```

**Voir les messages du topic views:**
```bash
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic views --from-beginning
```

**Voir les messages du topic ratings:**
```bash
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic ratings --from-beginning
```

### Lister les topics
```bash
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

## 📝 Exemple de workflow complet

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Démarrer Kafka
docker-compose up -d

# 3. Attendre 15 secondes que Kafka démarre
sleep 15  # Sur Windows PowerShell: Start-Sleep -Seconds 15

# 4. Créer les topics (optionnel)
python create_topics.py

# 5. Dans un nouveau terminal: Démarrer le producteur
python producer.py

# 6. Dans un autre terminal: Démarrer le consumer Spark
docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer

# 7. Laisser tourner pendant quelques minutes...

# 8. Ouvrir http://localhost:8080 pour voir les données dans Kafka UI

# 9. Vérifier les fichiers Parquet créés
dir data\parquet\clicks
dir data\parquet\views
dir data\parquet\ratings
```

## ✅ Checklist de vérification

Avant de considérer que tout fonctionne, vérifiez:

- [ ] Kafka est démarré (`docker-compose ps`)
- [ ] Kafka UI est accessible (http://localhost:8080)
- [ ] Le producteur envoie des données (logs visibles)
- [ ] Les topics existent dans Kafka UI (`clicks`, `views`, `ratings`)
- [ ] Des messages arrivent dans les topics (visible dans Kafka UI)
- [ ] Le consumer Spark est démarré et affiche "✅ Tous les streams sont actifs!"
- [ ] Des fichiers Parquet sont créés dans `data/parquet/`
- [ ] Les fichiers Parquet sont mis à jour régulièrement (toutes les 10 secondes)

## 🎯 Résultat attendu

Après avoir suivi ces étapes, vous devriez avoir:

1. ✅ Des données générées et envoyées à Kafka en temps réel
2. ✅ 3 topics Kafka actifs avec des données
3. ✅ Spark Streaming qui consomme les données depuis Kafka
4. ✅ Des fichiers Parquet créés et mis à jour toutes les 10 secondes
5. ✅ Une interface web (Kafka UI) pour visualiser les données

---

**Besoin d'aide?** Consultez le fichier `DOCKER_GUIDE.md` pour plus de détails sur Docker, ou `README.md` pour la documentation complète du projet.


