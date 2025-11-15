# メディアライブラリ機能 セットアップガイド

## 概要

このドキュメントは、WordPress風メディアライブラリ機能のセットアップ手順を説明します。

## 前提条件

- PostgreSQL データベースが稼働していること
- Google Cloud Storage (GCS) が設定されていること
- Python 仮想環境 `.venv` が有効化されていること
- サービスアカウント `gcp-credentials.json` が配置されていること

## セットアップ手順

### 1. データベースマイグレーション実行

```powershell
# 仮想環境を有効化
.venv\Scripts\activate

# マイグレーションスクリプトを実行
python scripts/migrate_add_media_table.py
```

マイグレーション内容:
- `media` テーブルの作成 (21フィールド)
- テナント分離のための `company_id` インデックス
- GCS統合のための `gcs_uri`, `gcs_bucket`, `gcs_path` フィールド
- メタデータ保存用 JSON フィールド

### 2. 環境変数の確認

`.env` ファイルに以下の設定があることを確認:

```env
# Google Cloud Storage
GOOGLE_APPLICATION_CREDENTIALS=gcp-credentials.json
GCS_BUCKET_NAME=kantan-ai-manual-generator
PROJECT_ID=kantan-ai-database
VERTEX_AI_LOCATION=us-central1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### 3. サーバー起動

```powershell
# VS Code タスクで起動 (推奨)
# Ctrl+Shift+P > Tasks: Run Task > 🚀 クリーンサーバー起動（ワンステップ）

# または手動起動
.venv\Scripts\activate
python app.py
```

### 4. 動作確認

#### 4.1 API エンドポイント確認

ブラウザまたは curl で確認:

```bash
# メディア一覧取得
curl http://localhost:5000/api/media/library

# 統計情報取得
curl http://localhost:5000/api/media/stats
```

#### 4.2 UI 確認

1. ブラウザで `http://localhost:5000` を開く
2. テストアカウントでログイン:
   - Company ID: `career-survival`
   - Email: `support@career-survival.com`
   - Password: `0000`
3. マニュアル編集画面を開く
4. TinyMCE ツールバーに「メディアライブラリ」ボタンが表示されることを確認

#### 4.3 メディアライブラリの動作確認

**アップロード機能:**
1. 「メディアライブラリ」ボタンをクリック
2. 「アップロード」ボタンをクリック
3. 画像ファイルを選択してアップロード
4. GCS にファイルがアップロードされることを確認
5. メディア一覧に表示されることを確認

**動画キャプチャ機能:**
1. 「キャプチャ」ボタンをクリック
2. 動画を選択
3. 任意のフレームでキャプチャ
4. キャプチャした画像が保存されることを確認

**画像編集機能:**
1. メディアアイテムの「編集」ボタンをクリック
2. 画像エディタが開くことを確認
3. 回転・反転機能を確認
4. 保存して新しい画像が作成されることを確認

**TinyMCE 統合:**
1. メディアライブラリで画像を選択
2. 「選択」ボタンをクリック
3. TinyMCE エディタに画像が挿入されることを確認

## トラブルシューティング

### エラー: "Media table already exists"

データベースに既に `media` テーブルが存在しています。マイグレーションをスキップするか、テーブルを削除してから再実行してください。

```sql
-- テーブル削除 (注意: データが失われます)
DROP TABLE IF EXISTS media CASCADE;
```

### エラー: "Could not automatically determine credentials"

GCS 認証情報が正しく設定されていません。

1. `gcp-credentials.json` がプロジェクトルートに存在することを確認
2. 環境変数 `GOOGLE_APPLICATION_CREDENTIALS` が設定されていることを確認
3. サービスアカウントに Storage Object Admin 権限があることを確認

### エラー: "Failed to register media routes"

メディア API ルートの登録に失敗しています。

1. `src/api/media_routes.py` が存在することを確認
2. 依存関係がインストールされていることを確認:
   ```powershell
   pip install -r requirements.txt
   ```

### メディアライブラリモーダルが表示されない

1. ブラウザの開発者ツールでコンソールエラーを確認
2. 以下のファイルが正しく読み込まれているか確認:
   - `/static/js/media_library.js`
   - `/components/media_library/media_library.css`
   - `/components/media_library/media_library_modal.html`

### 画像が TinyMCE に挿入されない

1. Signed URL の有効期限を確認 (デフォルト: 1時間)
2. GCS バケットのアクセス権限を確認
3. ブラウザのコンソールでネットワークエラーを確認

## 機能一覧

### 実装済み機能

✅ データベーススキーマ (Media モデル)
✅ バックエンド API (8エンドポイント)
✅ メディア管理サービス (GCS統合)
✅ メディアライブラリ UI (HTML/CSS/JS)
✅ 画像エディタ (スタンドアロン版)
✅ TinyMCE 統合 (manual_edit.html)
✅ テナント分離 (company_id)

### 主要エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/media/library` | メディア一覧取得 (ページネーション対応) |
| POST | `/api/media/upload` | ファイルアップロード |
| POST | `/api/media/capture-frame` | 動画フレームキャプチャ |
| GET | `/api/media/<id>` | メディア詳細取得 |
| PUT | `/api/media/<id>` | メディア情報更新 |
| DELETE | `/api/media/<id>` | メディア削除 (ソフトデリート) |
| GET | `/api/media/stats` | 統計情報取得 |

### ファイル構成

```
src/
├── api/
│   └── media_routes.py              # メディア API ルート
├── services/
│   └── media_manager.py             # メディア管理サービス
├── models/
│   └── models.py                    # Media モデル
├── static/
│   ├── js/
│   │   ├── media_library.js         # メディアライブラリ JS
│   │   └── image_editor_standalone.js  # 画像エディタ JS
│   └── css/
│       └── image_editor.css         # 画像エディタ CSS
├── components/
│   └── media_library/
│       ├── media_library_modal.html # メディアライブラリモーダル
│       └── media_library.css        # メディアライブラリ CSS
└── templates/
    └── manual_edit.html             # マニュアル編集画面 (統合済み)

scripts/
└── migrate_add_media_table.py       # マイグレーションスクリプト
```

## セキュリティ考慮事項

### テナント分離

すべてのメディア操作で `company_id` による分離を実施:
- API レベル: `current_user.company_id` でフィルタリング
- サービスレベル: `_enforce_tenant_isolation()` で検証
- データベースレベル: インデックスによる効率化

### アクセス制御

- ロールベース: `@require_role_enhanced(['admin', 'user'])`
- 認証必須: `@login_required` デコレータ
- CSRF 保護: Flask-WTF による自動保護

### ファイルセキュリティ

- GCS Signed URL: 期限付きアクセス (デフォルト 1時間)
- ファイルタイプ検証: 画像/動画のみ許可
- ファイルサイズ制限: アプリケーション設定に従う

## 次のステップ

1. **本番環境デプロイ前確認:**
   - データベースバックアップ
   - GCS バケット権限確認
   - 環境変数設定確認
   - ログ監視設定

2. **パフォーマンス最適化:**
   - メディアサムネイル生成
   - CDN 統合
   - キャッシュ戦略

3. **機能拡張:**
   - 画像クロップ機能
   - 複数ファイル一括アップロード
   - メディアフォルダ/タグ管理
   - 検索機能強化

## サポート

問題が発生した場合:
1. ログファイルを確認: `logs/app.log`
2. データベース状態を確認: `check_database_structure.py`
3. GCS 接続を確認: `check_gcs_buckets.py`
