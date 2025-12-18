# Script PowerShell pour redémarrer les services de manière séquentielle

Write-Host "🔄 Redémarrage des services du système de recommandation..." -ForegroundColor Cyan
Write-Host ""

# Fonction pour redémarrer un service
function Restart-Service {
    param(
        [string]$Service,
        [string]$Name
    )
    
    Write-Host "🔄 Redémarrage de $Name..." -ForegroundColor Yellow
    docker-compose restart $Service
    Start-Sleep -Seconds 2
    Write-Host "✅ $Name redémarré" -ForegroundColor Green
    Write-Host ""
}

# Redémarrer les services dans l'ordre de dépendance
Write-Host "📦 Services de base..." -ForegroundColor Cyan
Restart-Service -Service "postgres" -Name "PostgreSQL"
Restart-Service -Service "redis" -Name "Redis"
Restart-Service -Service "zookeeper" -Name "Zookeeper"

Write-Host "📡 Services de streaming..." -ForegroundColor Cyan
Restart-Service -Service "kafka" -Name "Kafka"

Write-Host "⚡ Services de traitement..." -ForegroundColor Cyan
Restart-Service -Service "spark-master" -Name "Spark Master"
Restart-Service -Service "spark-worker-1" -Name "Spark Worker 1"
Restart-Service -Service "spark-worker-2" -Name "Spark Worker 2"

Write-Host "🔄 Services d'orchestration..." -ForegroundColor Cyan
Restart-Service -Service "airflow-scheduler" -Name "Airflow Scheduler"
Restart-Service -Service "airflow-webserver" -Name "Airflow Webserver"
Restart-Service -Service "airflow-worker" -Name "Airflow Worker"

Write-Host "📊 Services de monitoring..." -ForegroundColor Cyan
Restart-Service -Service "mlflow" -Name "MLflow"
Restart-Service -Service "prometheus" -Name "Prometheus"
Restart-Service -Service "grafana" -Name "Grafana"

Write-Host "🌐 Services d'application..." -ForegroundColor Cyan
Restart-Service -Service "kafka-ui" -Name "Kafka UI"
Restart-Service -Service "fastapi" -Name "FastAPI"

Write-Host "✅ Tous les services ont été redémarrés!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 État des services:" -ForegroundColor Cyan
docker-compose ps




