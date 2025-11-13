@echo off
chcp 65001 >NUL
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   クリーンサーバー起動
echo ================================================
echo.

echo [1/5] すべてのPythonプロセスを停止中...
powershell -Command "Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Stop-Process -Force -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >NUL
echo       完了

echo.
echo [2/5] ElasticSearch ^& Redis を停止中...
docker-compose -f docker-compose.dev.yml down elasticsearch redis 2>NUL
timeout /t 2 /nobreak >NUL
echo       完了

echo.
echo [3/5] ElasticSearch ^& Redis を起動中...
docker-compose -f docker-compose.dev.yml up -d elasticsearch redis
timeout /t 5 /nobreak >NUL
echo       完了

echo.
echo [4/5] Docker サービス状態確認...
docker ps --filter "name=elasticsearch" --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

echo [5/5] Flask サーバー ^& Celery Worker 起動中...
echo.
call run_local_gunicorn.bat

endlocal
