# 🚀 Démarrage rapide

Guide ultra-rapide pour démarrer le projet en 5 minutes.

## ⚡ Commandes rapides

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Démarrer Kafka
docker-compose up -d

# 3. Attendre 15 secondes...

# 4. Créer les topics (optionnel)
python create_topics.py

# 5. Dans Terminal 1: Démarrer le producteur
python producer.py

# 6. Dans Terminal 2: Démarrer le consumer Spark
# Option A: Avec Docker (Recommandé)
docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer

# Option B: En local
python consumer_spark.py
# Note: Le package Kafka sera téléchargé automatiquement la première fois
```

## 📊 Vérification

- **Kafka UI:** http://localhost:8080
- **Fichiers Parquet:** `data/parquet/clicks/`, `data/parquet/views/`, `data/parquet/ratings/`

## ⏹️ Arrêter

```bash
# Ctrl+C dans les terminaux du producteur et consumer

# Arrêter Kafka
docker-compose down
```

---

📖 **Pour plus de détails:** Consultez [GUIDE_EXECUTION.md](GUIDE_EXECUTION.md)


