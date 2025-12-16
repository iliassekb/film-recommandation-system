# Guide de Démarrage Rapide

Ce guide vous permet de démarrer rapidement le système de recommandation de films.

## 🚀 Démarrage en 3 étapes

### Étape 1 : Prérequis

Assurez-vous d'avoir :
- ✅ Docker Desktop installé et en cours d'exécution
- ✅ Au moins 8GB de RAM disponible
- ✅ 20GB d'espace disque libre

### Étape 2 : Initialisation

**Windows (PowerShell) :**
```powershell
.\init.ps1
```

**Linux/Mac :**
```bash
chmod +x init.sh
./init.sh
```

Le script va :
1. Démarrer PostgreSQL
2. Créer la base de données MLflow
3. Démarrer tous les services
4. Initialiser Airflow

### Étape 3 : Vérification

Attendez 2-3 minutes que tous les services démarrent, puis vérifiez :

```bash
docker-compose ps
```

Tous les services doivent être en état "Up" (sauf `airflow-init` et `mlflow-init` qui s'exécutent une seule fois).

## 🌐 Accès aux Interfaces

Une fois démarré, accédez aux interfaces :

| Service | URL | Identifiants |
|---------|-----|--------------|
| **Kafka UI** | http://localhost:8080 | - |
| **Spark Master** | http://localhost:8081 | - |
| **Airflow** | http://localhost:8082 | admin / admin |
| **MLflow** | http://localhost:5000 | - |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **FastAPI** | http://localhost:8000 | - |
| **FastAPI Docs** | http://localhost:8000/docs | - |

## ✅ Test de Connectivité

Testez que tous les services communiquent correctement :

```bash
docker-compose exec fastapi python test-connections.py
```

Vous devriez voir tous les services marqués comme ✅.

## 📝 Premiers Pas

### 1. Créer un topic Kafka

```bash
docker-compose exec kafka kafka-topics --create \
  --topic films \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

### 2. Vérifier les DAGs Airflow

1. Allez sur http://localhost:8082
2. Connectez-vous avec admin/admin
3. Vous devriez voir le DAG d'exemple `film_recommendation_pipeline`

### 3. Tester l'API FastAPI

```bash
# Health check
curl http://localhost:8000/health

# Documentation interactive
# Ouvrez http://localhost:8000/docs dans votre navigateur
```

### 4. Vérifier MLflow

1. Allez sur http://localhost:5000
2. Vous devriez voir l'interface MLflow (vide pour l'instant)

## 🛠️ Commandes Utiles

### Voir les logs d'un service

```bash
docker-compose logs -f <service-name>
# Exemple: docker-compose logs -f kafka
```

### Redémarrer un service

```bash
docker-compose restart <service-name>
```

### Arrêter tous les services

```bash
docker-compose down
```

### Arrêter et supprimer les données

```bash
docker-compose down -v
```

⚠️ **Attention** : Cela supprime toutes les données persistées !

## 🔧 Configuration

### Modifier les ressources

Éditez `docker-compose.yml` pour ajuster :
- Mémoire des workers Spark : `SPARK_WORKER_MEMORY`
- Nombre de workers Spark : Ajoutez/supprimez des services `spark-worker-*`
- Ports : Modifiez les mappings de ports

### Ajouter des DAGs Airflow

Placez vos fichiers Python dans `airflow/dags/`. Ils seront automatiquement détectés.

### Personnaliser la configuration

Créez `docker-compose.override.yml` (basé sur `docker-compose.override.yml.example`) pour vos personnalisations locales.

## ❓ Problèmes Courants

### Les services ne démarrent pas

1. Vérifiez que Docker a assez de ressources (Settings > Resources)
2. Vérifiez les logs : `docker-compose logs <service-name>`
3. Vérifiez que les ports ne sont pas déjà utilisés

### Airflow affiche des erreurs

1. Attendez quelques minutes que l'initialisation se termine
2. Vérifiez les logs : `docker-compose logs airflow-init`
3. Réinitialisez : `docker-compose up airflow-init`

### Kafka ne fonctionne pas

1. Vérifiez que Zookeeper est démarré : `docker-compose ps zookeeper`
2. Vérifiez les logs : `docker-compose logs kafka zookeeper`

## 📚 Prochaines Étapes

1. **Créer vos DAGs Airflow** : Placez vos workflows dans `airflow/dags/`
2. **Développer l'API** : Modifiez `api/main.py` pour ajouter vos endpoints
3. **Configurer Spark** : Créez vos jobs Spark dans `spark/jobs/`
4. **Créer des dashboards Grafana** : Importez des dashboards dans `grafana/dashboards/`
5. **Utiliser MLflow** : Intégrez MLflow dans vos scripts d'entraînement

## 📖 Documentation Complète

Consultez le [README.md](README.md) pour plus de détails et le [CONNECTIONS.md](CONNECTIONS.md) pour les détails de connexion entre services.

