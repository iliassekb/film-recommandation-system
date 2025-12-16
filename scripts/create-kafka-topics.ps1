# Script PowerShell pour créer les topics Kafka nécessaires au système de recommandation

$KAFKA_CONTAINER = "kafka"
$BOOTSTRAP_SERVER = "localhost:9092"

Write-Host "📝 Création des topics Kafka pour le système de recommandation de films..." -ForegroundColor Cyan
Write-Host ""

# Fonction pour créer un topic
function Create-Topic {
    param(
        [string]$TopicName,
        [int]$Partitions = 3,
        [int]$ReplicationFactor = 1
    )
    
    Write-Host "Création du topic: $TopicName (partitions: $Partitions, replication: $ReplicationFactor)" -ForegroundColor Yellow
    
    $result = docker-compose exec -T $KAFKA_CONTAINER kafka-topics `
        --create `
        --topic $TopicName `
        --bootstrap-server $BOOTSTRAP_SERVER `
        --partitions $Partitions `
        --replication-factor $ReplicationFactor 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Topic '$TopicName' créé avec succès" -ForegroundColor Green
    } else {
        Write-Host "ℹ️  Topic '$TopicName' existe déjà ou erreur" -ForegroundColor Blue
    }
    Write-Host ""
}

# Créer les topics
Create-Topic -TopicName "film-ratings" -Partitions 3 -ReplicationFactor 1
Create-Topic -TopicName "film-recommendations" -Partitions 3 -ReplicationFactor 1
Create-Topic -TopicName "user-events" -Partitions 3 -ReplicationFactor 1
Create-Topic -TopicName "film-updates" -Partitions 3 -ReplicationFactor 1

Write-Host "📋 Liste des topics existants:" -ForegroundColor Cyan
docker-compose exec -T $KAFKA_CONTAINER kafka-topics `
    --list `
    --bootstrap-server $BOOTSTRAP_SERVER

Write-Host ""
Write-Host "✅ Création des topics terminée!" -ForegroundColor Green

