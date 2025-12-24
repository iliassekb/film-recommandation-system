@echo off
echo ========================================
echo   Demarrage du Consumer Spark avec Docker
echo ========================================
echo.
docker-compose -f docker-compose.yml -f docker-compose.spark.yml up spark-consumer
pause


