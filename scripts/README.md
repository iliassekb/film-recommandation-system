# Scripts Utilitaires

Ce dossier contient des scripts utilitaires pour faciliter la gestion du système.

## 📜 Scripts Disponibles

### 1. Création des Topics Kafka

#### `create-kafka-topics.sh` (Linux/Mac)
#### `create-kafka-topics.ps1` (Windows)

Crée automatiquement les topics Kafka nécessaires au système :
- `film-ratings` : Ratings des films
- `film-recommendations` : Recommandations générées
- `user-events` : Événements utilisateur
- `film-updates` : Mises à jour des films

**Utilisation:**
```bash
# Linux/Mac
chmod +x scripts/create-kafka-topics.sh
./scripts/create-kafka-topics.sh

# Windows
.\scripts\create-kafka-topics.ps1
```

### 2. Vérification des Services

#### `check-services.sh` (Linux/Mac)
#### `check-services.ps1` (Windows)

Vérifie l'état de tous les services et leur accessibilité.

**Utilisation:**
```bash
# Linux/Mac
chmod +x scripts/check-services.sh
./scripts/check-services.sh

# Windows
.\scripts\check-services.ps1
```

### 3. Redémarrage des Services

#### `restart-services.sh` (Linux/Mac)
#### `restart-services.ps1` (Windows)

Redémarre tous les services de manière séquentielle dans l'ordre de dépendance.

**Utilisation:**
```bash
# Linux/Mac
chmod +x scripts/restart-services.sh
./scripts/restart-services.sh

# Windows
.\scripts\restart-services.ps1
```

### 4. Sauvegarde des Données

#### `backup-data.sh` (Linux/Mac)
#### `backup-data.ps1` (Windows)

Sauvegarde les configurations, DAGs Airflow et données du lakehouse.

**Utilisation:**
```bash
# Linux/Mac
chmod +x scripts/backup-data.sh
./scripts/backup-data.sh

# Windows
.\scripts\backup-data.ps1
```

**Note:** Les volumes Docker doivent être sauvegardés séparément avec les commandes fournies dans le script.

### 5. Nettoyage

#### `cleanup.sh` (Linux/Mac)
#### `cleanup.ps1` (Windows)

Nettoie les fichiers temporaires, logs et fichiers compilés Python.

**Utilisation:**
```bash
# Linux/Mac
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh

# Windows
.\scripts\cleanup.ps1
```

**Options de nettoyage:**
- Logs Airflow
- Fichiers temporaires du lakehouse
- Checkpoints Spark
- Fichiers `__pycache__` et `.pyc`

## 🔧 Scripts Personnalisés

Vous pouvez créer vos propres scripts dans ce dossier pour :
- Automatiser des tâches répétitives
- Effectuer des opérations de maintenance
- Tester des fonctionnalités spécifiques
- Générer des rapports

## 💡 Exemples d'Utilisation

### Workflow Complet

1. **Démarrer le système**:
   ```bash
   .\init.ps1  # ou ./init.sh
   ```

2. **Vérifier les services**:
   ```bash
   .\scripts\check-services.ps1
   ```

3. **Créer les topics Kafka**:
   ```bash
   .\scripts\create-kafka-topics.ps1
   ```

4. **Tester la connectivité**:
   ```bash
   docker-compose exec fastapi python test-connections.py
   ```

### Maintenance Régulière

1. **Sauvegarder les données** (hebdomadaire):
   ```bash
   .\scripts\backup-data.ps1
   ```

2. **Nettoyer les fichiers temporaires** (mensuel):
   ```bash
   .\scripts\cleanup.ps1
   ```

3. **Redémarrer après une mise à jour**:
   ```bash
   .\scripts\restart-services.ps1
   ```

## 📝 Notes

- Tous les scripts sont conçus pour fonctionner avec Docker Compose
- Les scripts PowerShell sont optimisés pour Windows
- Les scripts Bash sont optimisés pour Linux/Mac
- Assurez-vous que Docker est en cours d'exécution avant d'utiliser les scripts

