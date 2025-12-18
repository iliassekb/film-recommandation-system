# Script pour vérifier l'état des workers Spark

Write-Host "🔍 Vérification des workers Spark..." -ForegroundColor Cyan
Write-Host ""

# Vérifier les workers
$workers = @("spark-worker-1", "spark-worker-2")

foreach ($worker in $workers) {
    $status = docker-compose ps $worker 2>&1
    if ($status -match "Up") {
        Write-Host "✅ $worker - En cours d'exécution" -ForegroundColor Green
    } else {
        Write-Host "❌ $worker - Arrêté" -ForegroundColor Red
        Write-Host "   Démarrer avec: docker-compose up -d $worker" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "📊 Spark Master UI: http://localhost:8081" -ForegroundColor Cyan
Write-Host "   Vérifiez la section 'Workers' pour voir les workers enregistrés" -ForegroundColor Yellow

