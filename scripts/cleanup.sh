#!/bin/bash

# Script de nettoyage pour supprimer les données temporaires et les logs

echo "🧹 Nettoyage du système de recommandation..."
echo ""

read -p "⚠️  Voulez-vous supprimer les logs Airflow? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Suppression des logs Airflow..."
    rm -rf airflow/logs/*
    echo "✅ Logs Airflow supprimés"
fi

read -p "⚠️  Voulez-vous supprimer les fichiers temporaires du lakehouse? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Suppression des fichiers temporaires..."
    find lakehouse -name "*.tmp" -delete
    find lakehouse -name "*.crc" -delete
    find lakehouse -name "_SUCCESS" -delete
    find lakehouse -name "_temporary" -type d -exec rm -rf {} + 2>/dev/null
    echo "✅ Fichiers temporaires supprimés"
fi

read -p "⚠️  Voulez-vous supprimer les checkpoints Spark? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Suppression des checkpoints..."
    find lakehouse -name "checkpoint" -type d -exec rm -rf {} + 2>/dev/null
    echo "✅ Checkpoints supprimés"
fi

read -p "⚠️  Voulez-vous supprimer les fichiers __pycache__? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Suppression des fichiers __pycache__..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -name "*.pyc" -delete
    find . -name "*.pyo" -delete
    echo "✅ Fichiers Python compilés supprimés"
fi

echo ""
echo "✅ Nettoyage terminé!"


