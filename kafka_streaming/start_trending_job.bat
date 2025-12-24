@echo off
echo ========================================
echo   Demarrage du Job Trending (Silver vers Gold)
echo   (stream_trending_to_gold)
echo ========================================
echo.
python spark\jobs\stream_trending_to_gold.py
pause

