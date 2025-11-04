@echo off
chcp 65001 >nul
setlocal
echo [Manual Generator] サーバー起動準備中...

REM ===== パス設定 =====
set "ROOT_DIR=%~dp0"
set "ROOT_VENV_PY=%ROOT_DIR%.venv\Scripts\python.exe"

REM ===== 仮想環境選択 =====
if exist "%ROOT_VENV_PY%" (
	set "USE_PY=%ROOT_VENV_PY%"
) else (
	echo 仮想環境が無いのでルートに作成します...
	where py >nul 2>nul && ( py -3 -m venv "%ROOT_DIR%.venv" ) || ( python -m venv "%ROOT_DIR%.venv" )
	if not exist "%ROOT_VENV_PY%" ( echo ルート仮想環境作成失敗 & exit /b 1 )
	set "USE_PY=%ROOT_VENV_PY%"
)

echo 使用Python: %USE_PY%

REM ===== 依存確認 (requests) =====
"%USE_PY%" -m pip show requests >nul 2>nul
if errorlevel 1 (
	echo 依存パッケージインストール開始...
	"%USE_PY%" -m pip install --upgrade pip || goto :ERROR
	"%USE_PY%" -m pip install -r requirements.txt || goto :ERROR
) else (
	echo 依存パッケージ: OK (requests)
)

REM ===== アプリ起動 =====
echo http://localhost:5000 にアクセスできます
"%USE_PY%" "%ROOT_DIR%app.py"
goto :END

:ERROR
echo *** 起動失敗: 依存インストールでエラー ***
exit /b 1

:END
endlocal
