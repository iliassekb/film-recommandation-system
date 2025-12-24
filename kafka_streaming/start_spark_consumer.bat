@echo off
echo ========================================
echo   Demarrage du Consumer Spark Streaming
echo   (stream_kafka_to_silver)
echo ========================================
echo.
python spark\jobs\stream_kafka_to_silver.py
pause

