@echo off
echo ========================================
echo   Demarrage de Kafka avec Docker
echo ========================================
echo.
docker-compose up -d
echo.
echo ✅ Kafka et Zookeeper demarres
echo 📊 Kafka UI disponible sur http://localhost:8080
echo.
pause


