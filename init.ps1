# Script d'initialisation PowerShell pour le système de recommandation de films
# Ce script crée les bases de données nécessaires et initialise les services

Write-Host "Initialisation du systeme de recommandation de films..." -ForegroundColor Cyan
Write-Host ""

# Vérifier si Docker est en cours d'exécution
try {
    docker info | Out-Null
    Write-Host "Docker est en cours d'execution" -ForegroundColor Green
} catch {
    Write-Host "Docker n'est pas en cours d'execution. Veuillez demarrer Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Démarrer PostgreSQL en premier
Write-Host "Demarrage de PostgreSQL..." -ForegroundColor Yellow
docker-compose up -d postgres

# Attendre que PostgreSQL soit prêt
Write-Host "Attente de PostgreSQL..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Vérifier que PostgreSQL est prêt
$maxAttempts = 30
$attempt = 0
$postgresReady = $false

while ($attempt -lt $maxAttempts -and -not $postgresReady) {
    try {
        docker-compose exec -T postgres pg_isready -U airflow 2>&1 | Out-Null
        $postgresReady = $true
        Write-Host "PostgreSQL est pret" -ForegroundColor Green
    } catch {
        $attempt++
        Write-Host "En attente de PostgreSQL... ($attempt/$maxAttempts)" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $postgresReady) {
    Write-Host "PostgreSQL n'a pas demarre dans le delai imparti" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Créer la base de données MLflow
Write-Host "Creation de la base de donnees MLflow..." -ForegroundColor Yellow
docker-compose exec -T postgres psql -U airflow -c "CREATE DATABASE mlflow;" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Base de donnees MLflow creee" -ForegroundColor Green
} else {
    Write-Host "La base de donnees MLflow existe deja" -ForegroundColor Blue
}

Write-Host ""

# Démarrer tous les services
Write-Host "Demarrage de tous les services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "Tous les services sont en cours de demarrage!" -ForegroundColor Green
Write-Host ""
Write-Host "Acces aux services:" -ForegroundColor Cyan
Write-Host "   - Kafka UI:        http://localhost:8080"
Write-Host "   - Spark Master:    http://localhost:8081"
Write-Host "   - Airflow:         http://localhost:8082 (admin/admin)"
Write-Host "   - MLflow:          http://localhost:5000"
Write-Host "   - Grafana:         http://localhost:3000 (admin/admin)"
Write-Host "   - Prometheus:      http://localhost:9090"
Write-Host "   - FastAPI:         http://localhost:8000"
Write-Host "   - FastAPI Docs:    http://localhost:8000/docs"
Write-Host ""
Write-Host "Attendez quelques instants que tous les services soient prets..." -ForegroundColor Yellow
Write-Host "   Vous pouvez verifier l'etat avec: docker-compose ps"
Write-Host "   Voir les logs avec: docker-compose logs -f service-name"
Write-Host ""
