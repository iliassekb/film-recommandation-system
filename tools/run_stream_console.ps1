# Script PowerShell pour exécuter le streaming Kafka → Console en mode CLUSTER
# Nécessite que les JARs Kafka soient installés sur tous les workers

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "run_stream_console_wrapper.py"

Write-Host "🚀 Démarrage du streaming Kafka → Console (MODE CLUSTER)" -ForegroundColor Cyan
Write-Host "ℹ️  Assurez-vous que les JARs Kafka sont installés: .\scripts\install_kafka_jars.ps1" -ForegroundColor Yellow
Write-Host ""

# Copier le script Python wrapper dans le conteneur
Write-Host "📋 Copie du script wrapper..." -ForegroundColor Yellow
docker cp $PythonScript spark-master:/tmp/run_stream_console_wrapper.py

# Exécuter le script Python wrapper
Write-Host "▶️  Exécution du streaming..." -ForegroundColor Green
Write-Host ""
docker-compose exec spark-master bash -c "python3 /tmp/run_stream_console_wrapper.py --mode cluster"

