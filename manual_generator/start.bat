@echo off
setlocal
echo Manual Generator起動中...

REM .venv が無ければ作成
if not exist ".venv\Scripts\python.exe" (
	echo .venv が見つかりません。作成しています...
	where py >nul 2>nul && ( py -3 -m venv .venv ) || ( python -m venv .venv )
)

REM 仮想環境をアクティベート
call .venv\Scripts\activate

REM 依存関係をインストール（必要な場合のみ最新化）
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt

REM Flaskアプリを起動
echo http://localhost:5000 でアクセスできます
python app.py

endlocal
