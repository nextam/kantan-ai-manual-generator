@echo off
chcp 65001 >NUL
setlocal ENABLEDELAYEDEXPANSION

echo ================================================
echo   クリーンサーバー起動
echo ================================================
echo.

echo [1/4] すべてのPythonプロセスを停止中...
powershell -Command "Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Stop-Process -Force -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >NUL
echo       完了

echo.
echo [2/4] ElasticSearch ^& Redis 再起動中...
docker-compose restart elasticsearch redis
timeout /t 3 /nobreak >NUL
echo       完了

echo.
echo [3/4] Docker サービス状態確認...
docker-compose ps elasticsearch redis
echo.

echo [4/4] Waitress サーバー起動中...
echo.
call run_local_gunicorn.bat

endlocal
