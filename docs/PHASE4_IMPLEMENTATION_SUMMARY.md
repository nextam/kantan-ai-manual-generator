# Phase 4 RAG System Implementation Summary

## 実装完了日
2025年11月5日

## 実装内容

### 1. 参照資料管理API (`src/api/material_routes.py`)
6つのエンドポイントを実装:

- **GET /api/materials** - 参照資料一覧取得
  - ページネーション対応
  - ファイルタイプ、処理状況でフィルタリング可能
  - 検索機能（タイトル、ファイル名）

- **POST /api/materials** - 参照資料アップロード
  - マルチパートファイルアップロード
  - S3ストレージへの自動アップロード
  - 非同期RAG処理タスクの起動

- **GET /api/materials/{id}** - 参照資料詳細取得
  - S3署名付きURLの生成
  - ダウンロードURL付き

- **GET /api/materials/{id}/status** - 処理状況確認
  - 処理進捗（0-100%）
  - エラーメッセージ
  - ElasticSearchインデックス状況

- **PUT /api/materials/{id}** - 参照資料更新
  - タイトル、説明、アクティブ状態の更新

- **DELETE /api/materials/{id}** - 参照資料削除
  - ソフト削除
  - ElasticSearchからの削除

### 2. ElasticSearchサービス (`src/services/elasticsearch_service.py`)
ElasticSearch統合機能:

- **インデックス管理**
  - 自動インデックス作成
  - dense_vectorフィールド（768次元）
  - 日本語解析（Kuromoji）

- **ベクトル検索**
  - コサイン類似度検索
  - company_idフィルタリング
  - Top-k取得

- **ハイブリッド検索**
  - ベクトル検索 + BM25キーワード検索
  - 重み調整可能

- **CRUD操作**
  - チャンクインデックス化
  - マテリアル削除
  - チャンク数カウント

### 3. RAG処理パイプライン (`src/services/rag_processor.py`)
テキスト抽出からインデックス化までの完全パイプライン:

- **テキスト抽出**
  - PDF: pdfplumber (高品質) → PyPDF2 (フォールバック)
  - Word: python-docx（段落、テーブル）
  - Excel: openpyxl（シート、行）
  - CSV: テキスト読み込み

- **Geminiメタデータ抽出**
  - ドキュメントタイプ分類
  - キートピック抽出（3-5件）
  - サマリー生成

- **チャンク化**
  - 段落ベース分割
  - 目標サイズ: 1000トークン
  - オーバーラップ: 50トークン

- **埋め込み生成**
  - Vertex AI text-embedding-004
  - 768次元ベクトル
  - バッチ処理（100件ずつ）

### 4. Celeryワーカー (`src/workers/celery_app.py`)
非同期タスク処理の設定:

- **Redis統合**
  - メッセージブローカー: Redis DB 1
  - リザルトバックエンド: Redis DB 2

- **キュー管理**
  - default: 汎用タスク
  - rag_processing: RAG処理専用
  - pdf_generation: PDF生成用
  - translation: 翻訳用

- **タスク設定**
  - タイムアウト: 1時間
  - リトライ: 3回
  - タスク追跡有効化

### 5. RAG非同期タスク (`src/workers/rag_tasks.py`)
Celeryタスク実装:

- **process_material_task**
  - 完全なRAG処理パイプライン実行
  - 進捗トラッキング（ProcessingJob更新）
  - エラーハンドリング
  - データベース＋ElasticSearch更新

- **reindex_material_task**
  - 既存チャンクの再インデックス化（プレースホルダー）

- **cleanup_failed_jobs**
  - 失敗ジョブのクリーンアップ（7日以上）

## データフロー

```
1. ファイルアップロード (POST /api/materials)
   ↓
2. S3保存 (company_id/materials/material_id/)
   ↓
3. データベース登録 (ReferenceMaterial, ProcessingJob)
   ↓
4. Celeryタスク起動 (process_material_task)
   ↓
5. RAG処理パイプライン
   ├─ S3ダウンロード
   ├─ テキスト抽出
   ├─ Geminiメタデータ抽出
   ├─ チャンク化
   ├─ 埋め込み生成
   └─ ElasticSearchインデックス化
   ↓
6. データベース更新
   ├─ ReferenceMaterial (processing_status='completed')
   ├─ ReferenceChunk (全チャンク保存)
   └─ ProcessingJob (job_status='completed')
```

## セキュリティ

- **テナント分離**
  - 全S3パス: `{company_id}/materials/...`
  - ElasticSearchフィルタ: `company_id`
  - API認証: `@require_role_enhanced`

- **アクセス制御**
  - S3署名付きURL（1時間有効）
  - company_idバリデーション
  - アクティビティログ記録

## テスト

### テストスクリプト (`scripts/test_phase4_rag.py`)
包括的なテストスイート:

1. 認証テスト
2. ElasticSearchヘルスチェック
3. マテリアル一覧取得
4. マテリアルアップロード
5. 処理状況ポーリング
6. マテリアル詳細取得
7. マテリアル更新
8. マテリアル削除（オプション）

### テスト実行方法

```powershell
# サーバー起動
# VS Code Task: "マニュアル生成サーバー起動 (ポート5000) - Waitress"

# ElasticSearch起動（別ターミナル）
cd kantan-ai-manual-generator
docker-compose -f docker-compose.dev.yml up -d

# Celeryワーカー起動（別ターミナル）
.venv\Scripts\activate
celery -A src.workers.celery_app worker --loglevel=info -P solo

# テスト実行
.venv\Scripts\activate
python scripts\test_phase4_rag.py
```

## 依存関係

### 新規インストールパッケージ
- boto3==1.34.0 (AWS S3)
- elasticsearch==8.11.0 (ElasticSearch)
- redis==5.0.1 (Redis)
- celery==5.3.4 (非同期処理)
- flower==2.0.1 (Celery監視)
- PyPDF2==3.0.1 (PDF抽出)
- pdfplumber==0.10.3 (PDF抽出)
- python-docx==1.1.0 (Word抽出)
- openpyxl==3.1.2 (Excel抽出)
- weasyprint==60.1 (PDF生成 - Phase 6用)
- faker==20.1.0 (テストデータ)

### インフラ要件
- ElasticSearch 8.11.0
- Redis 7.x
- AWS S3アクセス（credentials設定必要）

## 環境変数

`.env`に以下を追加済み:

```bash
# AWS S3
AWS_S3_BUCKET_NAME=kantan-ai-manual-generator
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=（設定必要）
AWS_SECRET_ACCESS_KEY=（設定必要）

# ElasticSearch
ELASTICSEARCH_URL=http://localhost:9200

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## 既知の制限事項

1. **S3認証情報**
   - AWS_ACCESS_KEY_ID と AWS_SECRET_ACCESS_KEY の設定が必要
   - 本番環境ではIAMロール使用を推奨

2. **ElasticSearch Kuromoji**
   - 日本語解析にはKuromojiプラグインが必要
   - Dockerイメージには含まれていない場合あり

3. **Celeryワーカー**
   - Windows環境では `-P solo` オプション必須
   - 本番環境ではLinux推奨

4. **埋め込み再生成**
   - reindex_material_taskは未実装
   - 再処理には完全なRAG処理が必要

## 次のステップ（Phase 5以降）

1. **Phase 5: マニュアル生成強化**
   - テンプレート統合
   - RAG検索によるコンテキスト注入
   - バッチ生成

2. **Phase 6: PDF出力**
   - WeasyPrintによるPDF生成
   - A4サイズ最適化
   - テンプレートカスタマイズ

3. **Phase 7: 多言語翻訳**
   - Gemini翻訳API統合
   - バッチ翻訳
   - フォーマット保持

## トラブルシューティング

### ElasticSearchに接続できない
```powershell
# ElasticSearchステータス確認
docker-compose -f docker-compose.dev.yml ps

# ログ確認
docker-compose -f docker-compose.dev.yml logs elasticsearch

# 再起動
docker-compose -f docker-compose.dev.yml restart elasticsearch
```

### Celeryタスクが実行されない
```powershell
# Redisステータス確認
docker-compose -f docker-compose.dev.yml ps redis

# Celeryワーカーログ確認
# ワーカー起動時のターミナルを確認

# ワーカー再起動
# Ctrl+C で停止後、再度起動
celery -A src.workers.celery_app worker --loglevel=info -P solo
```

### S3アップロードエラー
```powershell
# AWS認証情報確認
echo $env:AWS_ACCESS_KEY_ID
echo $env:AWS_SECRET_ACCESS_KEY

# .envファイル確認
cat .env | Select-String AWS
```

## 実装ファイル一覧

- `src/api/material_routes.py` (新規作成 - 400行)
- `src/services/elasticsearch_service.py` (新規作成 - 360行)
- `src/services/rag_processor.py` (新規作成 - 440行)
- `src/workers/celery_app.py` (新規作成 - 120行)
- `src/workers/rag_tasks.py` (新規作成 - 250行)
- `scripts/test_phase4_rag.py` (新規作成 - 380行)
- `src/core/app.py` (Blueprint登録追加)
- `docker-compose.dev.yml` (既存 - Phase 4環境セットアップ時作成済み)
- `requirements.txt` (既存 - Phase 4パッケージ追加済み)
- `.env` (既存 - Phase 4環境変数追加済み)
