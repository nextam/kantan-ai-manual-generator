@echo off
REM Set Google Cloud credentials for local development
REM This script sets the GOOGLE_APPLICATION_CREDENTIALS environment variable

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set CREDENTIALS_FILE=%PROJECT_ROOT%\gcp-credentials.json

echo Checking for GCP credentials file...

if exist "%CREDENTIALS_FILE%" (
    echo [OK] Found gcp-credentials.json
    
    REM Set environment variable for current session
    set GOOGLE_APPLICATION_CREDENTIALS=%CREDENTIALS_FILE%
    
    REM Also set PROJECT_ID from .env if it exists
    if exist "%PROJECT_ROOT%\.env" (
        echo [OK] Loading environment variables from .env
        for /f "tokens=1,2 delims==" %%a in ('type "%PROJECT_ROOT%\.env" ^| findstr /v "^#"') do (
            set %%a=%%b
        )
    )
    
    echo.
    echo Environment variables set:
    echo   GOOGLE_APPLICATION_CREDENTIALS=%CREDENTIALS_FILE%
    if defined PROJECT_ID echo   PROJECT_ID=%PROJECT_ID%
    if defined GCS_BUCKET_NAME echo   GCS_BUCKET_NAME=%GCS_BUCKET_NAME%
    if defined VERTEX_AI_LOCATION echo   VERTEX_AI_LOCATION=%VERTEX_AI_LOCATION%
    
    echo.
    echo [OK] Ready to run server with GCP credentials
    
) else (
    echo [ERROR] gcp-credentials.json not found!
    echo Expected location: %CREDENTIALS_FILE%
    exit /b 1
)
