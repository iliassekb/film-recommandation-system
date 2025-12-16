# Script PowerShell pour vérifier l'état de tous les services

Write-Host "🔍 Vérification de l'état des services..." -ForegroundColor Cyan
Write-Host ""

# Fonction pour vérifier un service
function Check-Service {
    param(
        [string]$Service,
        [int]$Port = 0,
        [string]$Name
    )
    
    $status = docker-compose ps $Service 2>&1
    if ($status -match "Up") {
        if ($Port -gt 0) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$Port" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Host "✅ $Name - En cours d'exécution (port $Port)" -ForegroundColor Green
                } else {
                    Write-Host "⚠️  $Name - Conteneur démarré mais port $Port non accessible" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "⚠️  $Name - Conteneur démarré mais port $Port non accessible" -ForegroundColor Yellow
            }
        } else {
            Write-Host "✅ $Name - En cours d'exécution" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ $Name - Arrêté" -ForegroundColor Red
    }
}

# Vérifier tous les services
Check-Service -Service "zookeeper" -Name "Zookeeper"
Check-Service -Service "kafka" -Port 9092 -Name "Kafka"
Check-Service -Service "kafka-ui" -Port 8080 -Name "Kafka UI"
Check-Service -Service "postgres" -Port 5432 -Name "PostgreSQL"
Check-Service -Service "redis" -Port 6379 -Name "Redis"
Check-Service -Service "spark-master" -Port 8081 -Name "Spark Master"
Check-Service -Service "spark-worker-1" -Name "Spark Worker 1"
Check-Service -Service "spark-worker-2" -Name "Spark Worker 2"
Check-Service -Service "airflow-webserver" -Port 8082 -Name "Airflow Webserver"
Check-Service -Service "airflow-scheduler" -Name "Airflow Scheduler"
Check-Service -Service "airflow-worker" -Name "Airflow Worker"
Check-Service -Service "mlflow" -Port 5000 -Name "MLflow"
Check-Service -Service "prometheus" -Port 9090 -Name "Prometheus"
Check-Service -Service "grafana" -Port 3000 -Name "Grafana"
Check-Service -Service "fastapi" -Port 8000 -Name "FastAPI"

Write-Host ""
Write-Host "📊 Résumé:" -ForegroundColor Cyan
docker-compose ps

