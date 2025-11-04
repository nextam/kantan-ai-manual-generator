#!/bin/bash
echo "Manual Generator起動中..."

# 依存関係をインストール
pip install -r requirements.txt

# Flaskアプリを起動
echo "http://localhost:5000 でアクセスできます"
python app.py
