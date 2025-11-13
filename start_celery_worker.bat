@echo off
chcp 65001 >NUL
echo ================================================
echo   Celery Worker 起動
echo ================================================
echo.

cd /d %~dp0

echo 仮想環境をアクティベート中...
call .venv\Scripts\activate.bat

echo.
echo Celery Worker を起動中...
echo ログ: logs\celery_worker.log
echo.

celery -A src.workers.celery_app:celery worker --loglevel=info --logfile=logs\celery_worker.log --pool=solo
