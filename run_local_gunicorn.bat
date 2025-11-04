@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >NUL

echo [INFO] Starting Waitress (Windows-compatible WSGI server)...

REM 優先順に仮想環境パス候補を探索 (.venv, venv, repo 直下指定)
set CANDIDATES=.venv;venv
set VENV_PATH=
for %%p in (%CANDIDATES%) do (
    if exist "%%p\Scripts\activate" (
        set VENV_PATH=%%p
        goto :found
    )
)
:found
if "%VENV_PATH%"=="" (
    echo [INFO] Virtual env not found. Creating .venv
    py -3 -m venv .venv
    set VENV_PATH=.venv
)

call "%VENV_PATH%\Scripts\activate" || (
    echo [ERROR] Failed to activate virtual environment & exit /b 1
)

REM 依存関係インストール (キャッシュ利用で高速化)
if exist manual_generator\requirements.txt (
    echo [INFO] Installing dependencies from requirements.txt
    pip install -r manual_generator\requirements.txt >NUL
)

pushd manual_generator

echo [INFO] Launch waitress (port 5000)
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 --connection-limit=1000 --cleanup-interval=30 --channel-timeout=120 --max-request-body-size=10737418240 app:app
popd

endlocal
