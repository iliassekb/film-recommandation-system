# Script PowerShell de sauvegarde des données importantes

$BackupDir = ".\backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = Join-Path $BackupDir "backup_$Timestamp"

Write-Host "💾 Sauvegarde des données du système de recommandation..." -ForegroundColor Cyan
Write-Host ""

# Créer le dossier de backup
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $BackupPath | Out-Null

# Sauvegarder les configurations
Write-Host "📄 Sauvegarde des configurations..." -ForegroundColor Yellow
$configFiles = @(
    "airflow\config",
    "spark\config",
    "prometheus",
    "grafana\provisioning",
    "api",
    "docker-compose.yml"
)

$configPath = Join-Path $BackupPath "configs.tar.gz"
# Note: PowerShell n'a pas tar natif sur toutes les versions
# Utilisez 7zip ou tar si disponible
if (Get-Command tar -ErrorAction SilentlyContinue) {
    tar -czf $configPath $configFiles 2>$null
} else {
    Write-Host "⚠️  tar non disponible. Veuillez installer tar ou 7zip pour la compression." -ForegroundColor Yellow
    Copy-Item -Path $configFiles -Destination $BackupPath -Recurse -Force
}

# Sauvegarder les DAGs Airflow
Write-Host "📋 Sauvegarde des DAGs Airflow..." -ForegroundColor Yellow
if (Test-Path "airflow\dags") {
    $dagsPath = Join-Path $BackupPath "airflow_dags"
    Copy-Item -Path "airflow\dags" -Destination $dagsPath -Recurse -Force
}

# Sauvegarder les données du lakehouse
Write-Host "💾 Sauvegarde du lakehouse..." -ForegroundColor Yellow
if (Test-Path "lakehouse" -PathType Container) {
    $files = Get-ChildItem -Path "lakehouse" -File
    if ($files.Count -gt 0) {
        $lakehousePath = Join-Path $BackupPath "lakehouse"
        Copy-Item -Path "lakehouse" -Destination $lakehousePath -Recurse -Force
    }
}

Write-Host ""
Write-Host "📦 Pour sauvegarder les volumes Docker, utilisez:" -ForegroundColor Cyan
Write-Host "   docker run --rm -v postgres-data:/data -v `$(pwd)/$BackupPath:/backup \"
Write-Host "     alpine tar czf /backup/postgres-data.tar.gz -C /data ."
Write-Host ""
Write-Host "   Répétez pour chaque volume:"
Write-Host "   - postgres-data"
Write-Host "   - redis-data"
Write-Host "   - kafka-data"
Write-Host "   - mlflow-artifacts"
Write-Host "   - prometheus-data"
Write-Host "   - grafana-data"

$size = (Get-ChildItem -Path $BackupPath -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ""
Write-Host "✅ Sauvegarde terminée: $BackupPath" -ForegroundColor Green
Write-Host "📊 Taille: $([math]::Round($size, 2)) MB" -ForegroundColor Green


