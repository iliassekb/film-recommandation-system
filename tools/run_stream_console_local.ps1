# Script PowerShell pour exécuter le streaming Kafka → Console en mode LOCAL
# Mode local = exécution sur le driver uniquement (pas besoin de workers ou de JARs installés)
# Utile pour tester avec des ressources limitées

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "run_stream_console_wrapper.py"

Write-Host "🚀 Démarrage du streaming Kafka → Console (MODE LOCAL)" -ForegroundColor Cyan
Write-Host ""

# Copier le script Python wrapper dans le conteneur
Write-Host "📋 Copie du script wrapper..." -ForegroundColor Yellow
docker cp $PythonScript spark-master:/tmp/run_stream_console_wrapper.py

# Exécuter le script Python wrapper
Write-Host "▶️  Exécution du streaming..." -ForegroundColor Green
Write-Host ""
docker-compose exec spark-master bash -c "python3 /tmp/run_stream_console_wrapper.py --mode local"

# Nettoyer (optionnel)
# docker-compose exec spark-master rm -f /tmp/run_stream_console_wrapper.py

