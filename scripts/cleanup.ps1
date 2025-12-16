# Script PowerShell de nettoyage pour supprimer les données temporaires

Write-Host "🧹 Nettoyage du système de recommandation..." -ForegroundColor Cyan
Write-Host ""

$response = Read-Host "⚠️  Voulez-vous supprimer les logs Airflow? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "🗑️  Suppression des logs Airflow..." -ForegroundColor Yellow
    if (Test-Path "airflow\logs") {
        Remove-Item -Path "airflow\logs\*" -Recurse -Force
        Write-Host "✅ Logs Airflow supprimés" -ForegroundColor Green
    }
}

$response = Read-Host "⚠️  Voulez-vous supprimer les fichiers temporaires du lakehouse? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "🗑️  Suppression des fichiers temporaires..." -ForegroundColor Yellow
    Get-ChildItem -Path "lakehouse" -Recurse -Include "*.tmp", "*.crc", "_SUCCESS" | Remove-Item -Force
    Get-ChildItem -Path "lakehouse" -Recurse -Directory -Filter "_temporary" | Remove-Item -Recurse -Force
    Write-Host "✅ Fichiers temporaires supprimés" -ForegroundColor Green
}

$response = Read-Host "⚠️  Voulez-vous supprimer les checkpoints Spark? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "🗑️  Suppression des checkpoints..." -ForegroundColor Yellow
    Get-ChildItem -Path "lakehouse" -Recurse -Directory -Filter "checkpoint" | Remove-Item -Recurse -Force
    Write-Host "✅ Checkpoints supprimés" -ForegroundColor Green
}

$response = Read-Host "⚠️  Voulez-vous supprimer les fichiers __pycache__? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "🗑️  Suppression des fichiers __pycache__..." -ForegroundColor Yellow
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Include "*.pyc", "*.pyo" | Remove-Item -Force
    Write-Host "✅ Fichiers Python compilés supprimés" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ Nettoyage terminé!" -ForegroundColor Green


