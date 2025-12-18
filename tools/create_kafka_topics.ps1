# Script PowerShell pour créer les topics Kafka nécessaires au streaming

Write-Host "🔧 Création des topics Kafka pour le streaming..." -ForegroundColor Cyan
Write-Host ""

$KAFKA_BOOTSTRAP_SERVER = "localhost:29092"

# Fonction pour créer un topic
function Create-Topic {
    param(
        [string]$TopicName,
        [int]$Partitions = 3,
        [int]$ReplicationFactor = 1,
        [string]$RetentionMs
    )
    
    Write-Host "Création du topic: $TopicName (partitions: $Partitions, retention: $RetentionMs ms)" -ForegroundColor Yellow
    
    $result = docker-compose exec -T kafka kafka-topics `
        --create `
        --topic $TopicName `
        --bootstrap-server $KAFKA_BOOTSTRAP_SERVER `
        --partitions $Partitions `
        --replication-factor $ReplicationFactor `
        --config retention.ms=$RetentionMs `
        --if-not-exists 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Topic '$TopicName' créé avec succès" -ForegroundColor Green
    } else {
        if ($result -match "already exists") {
            Write-Host "ℹ️  Topic '$TopicName' existe déjà" -ForegroundColor Blue
        } else {
            Write-Host "❌ Erreur lors de la création: $result" -ForegroundColor Red
        }
    }
    Write-Host ""
}

Write-Host "Option 1: Utiliser le script Python (Recommandé)" -ForegroundColor Cyan
Write-Host "Exécution: docker-compose run --rm kafka-topic-init" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 2: Créer les topics manuellement" -ForegroundColor Cyan
Write-Host ""

# Créer les topics
Create-Topic -TopicName "events_views" -Partitions 3 -ReplicationFactor 1 -RetentionMs "604800000"
Create-Topic -TopicName "events_clicks" -Partitions 3 -ReplicationFactor 1 -RetentionMs "604800000"
Create-Topic -TopicName "events_ratings" -Partitions 3 -ReplicationFactor 1 -RetentionMs "2592000000"

Write-Host "📋 Liste des topics existants:" -ForegroundColor Cyan
docker-compose exec -T kafka kafka-topics `
    --list `
    --bootstrap-server $KAFKA_BOOTSTRAP_SERVER

Write-Host ""
Write-Host "✅ Création des topics terminée!" -ForegroundColor Green

