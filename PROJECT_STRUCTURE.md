# Structure du Projet

```
Films-recommandation-system/
│
├── docker-compose.yml              # Configuration principale Docker Compose
├── docker-compose.override.yml.example  # Exemple de configuration personnalisée
│
├── README.md                        # Documentation principale
├── QUICK_START.md                   # Guide de démarrage rapide
├── CONNECTIONS.md                   # Guide des connexions entre services
├── PROJECT_STRUCTURE.md             # Ce fichier
│
├── init.sh                          # Script d'initialisation (Linux/Mac)
├── init.ps1                         # Script d'initialisation (Windows)
├── test-connections.py              # Script de test de connectivité
│
├── api/                             # Application FastAPI
│   ├── Dockerfile                   # Image Docker pour FastAPI
│   ├── requirements.txt             # Dépendances Python
│   ├── main.py                      # Application principale
│   ├── .dockerignore               # Fichiers ignorés par Docker
│   └── .env.example                # Exemple de variables d'environnement
│
├── airflow/                         # Configuration Airflow
│   ├── dags/                        # DAGs Airflow
│   │   └── example_dag.py          # DAG d'exemple
│   ├── logs/                        # Logs Airflow (générés automatiquement)
│   ├── plugins/                     # Plugins Airflow personnalisés
│   └── config/                      # Configuration Airflow
│       ├── airflow.cfg             # Configuration principale
│       ├── connections.yaml        # Connexions par défaut
│       ├── requirements.txt         # Dépendances Python supplémentaires
│       └── webserver_config.py     # Configuration webserver
│
├── spark/                           # Configuration Spark
│   └── config/
│       ├── spark-defaults.conf     # Configuration Spark par défaut
│       └── log4j2.properties        # Configuration des logs
│
├── prometheus/                      # Configuration Prometheus
│   ├── prometheus.yml              # Configuration principale
│   └── alerts.yml                  # Règles d'alerte
│
├── grafana/                         # Configuration Grafana
│   ├── dashboards/                  # Dashboards personnalisés
│   └── provisioning/                # Configuration automatique
│       ├── datasources/
│       │   └── prometheus.yml      # Datasource Prometheus
│       └── dashboards/
│           └── dashboard.yml       # Configuration des dashboards
│
└── lakehouse/                       # Stockage des données (Delta/Parquet)
    └── .gitkeep                    # Fichier pour garder le dossier dans Git
```

## Description des Composants

### Configuration Docker

- **docker-compose.yml** : Définit tous les services et leurs configurations
- **docker-compose.override.yml.example** : Template pour personnalisations locales

### Scripts

- **init.sh / init.ps1** : Scripts d'initialisation automatique
- **test-connections.py** : Vérifie la connectivité entre tous les services

### API FastAPI

L'application FastAPI sert les recommandations et expose une API REST.

### Airflow

- **dags/** : Contient les workflows orchestrés par Airflow
- **config/** : Configuration et connexions Airflow
- **plugins/** : Plugins personnalisés pour étendre Airflow

### Spark

Configuration pour le traitement distribué des données.

### Monitoring

- **Prometheus** : Collecte les métriques
- **Grafana** : Visualisation des métriques et dashboards

### Lakehouse

Stockage centralisé pour les données en format Delta/Parquet, accessible par tous les services.

## Volumes Docker

Les volumes suivants sont créés automatiquement :

- `zookeeper-data` : Données Zookeeper
- `kafka-data` : Données Kafka
- `postgres-data` : Base de données PostgreSQL
- `redis-data` : Données Redis
- `spark-data` : Données Spark
- `mlflow-artifacts` : Artifacts MLflow
- `prometheus-data` : Données Prometheus
- `grafana-data` : Données Grafana

## Fichiers Générés Automatiquement

Ces fichiers/dossiers sont créés automatiquement et ne doivent pas être commités :

- `airflow/logs/` : Logs Airflow
- `lakehouse/*.parquet` : Fichiers de données
- `lakehouse/*.delta` : Tables Delta
- `.env` : Variables d'environnement locales

Ils sont listés dans `.gitignore`.

