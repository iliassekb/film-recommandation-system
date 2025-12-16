#!/bin/bash

# Script de sauvegarde des données importantes
# Ce script sauvegarde les volumes Docker et les configurations

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

echo "💾 Sauvegarde des données du système de recommandation..."
echo ""

# Créer le dossier de backup
mkdir -p "$BACKUP_PATH"

# Sauvegarder les configurations
echo "📄 Sauvegarde des configurations..."
tar -czf "$BACKUP_PATH/configs.tar.gz" \
    airflow/config/ \
    spark/config/ \
    prometheus/ \
    grafana/provisioning/ \
    api/ \
    docker-compose.yml \
    2>/dev/null

# Sauvegarder les DAGs Airflow
echo "📋 Sauvegarde des DAGs Airflow..."
if [ -d "airflow/dags" ]; then
    tar -czf "$BACKUP_PATH/airflow_dags.tar.gz" airflow/dags/ 2>/dev/null
fi

# Sauvegarder les données du lakehouse (si elles existent)
echo "💾 Sauvegarde du lakehouse..."
if [ -d "lakehouse" ] && [ "$(ls -A lakehouse)" ]; then
    tar -czf "$BACKUP_PATH/lakehouse.tar.gz" lakehouse/ 2>/dev/null
fi

# Instructions pour sauvegarder les volumes Docker
echo ""
echo "📦 Pour sauvegarder les volumes Docker, utilisez:"
echo "   docker run --rm -v postgres-data:/data -v \$(pwd)/$BACKUP_PATH:/backup \\"
echo "     alpine tar czf /backup/postgres-data.tar.gz -C /data ."
echo ""
echo "   Répétez pour chaque volume:"
echo "   - postgres-data"
echo "   - redis-data"
echo "   - kafka-data"
echo "   - mlflow-artifacts"
echo "   - prometheus-data"
echo "   - grafana-data"

echo ""
echo "✅ Sauvegarde terminée: $BACKUP_PATH"
echo "📊 Taille: $(du -sh $BACKUP_PATH | cut -f1)"


