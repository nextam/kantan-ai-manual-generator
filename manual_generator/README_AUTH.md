# Manual Generator 企業認証対応版

企業テナント機能を搭載したマニュアル自動生成システムです。Gemini 2.5 Pro AIを活用して、製造業向けの高品質なマニュアルを自動生成します。

## 🆕 新機能

### 1. 企業テナント機能
- 企業ごとのデータ分離
- 企業コード + パスワードによる認証
- 企業内ユーザー管理

### 2. データ保存機能
- アップロードファイルの履歴保存
- 生成マニュアルの履歴管理
- 企業設定・出力設定の保存

### 3. ストレージ選択
- **ローカルストレージ**: EC2内でデータ完結
- **Google Cloud Storage**: クラウドストレージ（オプション）
- **Amazon S3**: クラウドストレージ（オプション）

## 📋 システム要件

- Python 3.8+
- Flask 3.0+
- SQLite（デフォルト）/ PostgreSQL / MySQL
- Google Cloud API認証情報

## 🚀 クイックスタート

### 1. 依存関係インストール

```bash
cd manual_generator
pip install -r requirements.txt
```

### 2. データベース初期化

```bash
# データベースとサンプル企業を作成
python db_manager.py init
```

サンプル企業が自動作成されます：
- **企業1**: サンプル製造業株式会社 (コード: `sample001`, パスワード: `password123`)
- **企業2**: テスト工業有限会社 (コード: `test002`, パスワード: `test123456`)

### 3. アプリケーション起動

```bash
# 認証機能付きバージョンを起動
python app_with_auth.py
```

### 4. ログイン

1. ブラウザで `http://localhost:5000` にアクセス
2. 企業コード、パスワード、ユーザー名（通常は`admin`）を入力
3. ログイン後、マニュアル生成機能が利用可能

## 🏢 企業管理

### 新規企業作成

```bash
# 対話式で企業作成
python db_manager.py create
```

### 企業一覧表示

```bash
python db_manager.py list
```

### データベース管理

```bash
# データベースバックアップ
python db_manager.py backup

# データベース復元
python db_manager.py restore --backup-file backup_file.db

# 孤立ファイル清掃
python db_manager.py clean
```

## ⚙️ 設定

### 環境変数

```bash
# .envファイルに設定
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///manual_generator.db
GOOGLE_API_KEY=your-google-api-key
```

### データベース設定

デフォルトではSQLiteを使用しますが、本格運用時はPostgreSQLまたはMySQLを推奨：

```bash
# PostgreSQL例
DATABASE_URL=postgresql://user:password@localhost/manual_generator

# MySQL例  
DATABASE_URL=mysql://user:password@localhost/manual_generator
```

### ストレージ設定

企業設定画面から以下を選択可能：

1. **ローカルストレージ**（推奨）
   - EC2内のディスクを使用
   - 追加コストなし
   - バックアップが重要

2. **Google Cloud Storage**
   - スケーラブル
   - 認証情報ファイルが必要

3. **Amazon S3**
   - AWS統合環境で有効
   - IAMキーが必要

## 🔒 セキュリティ

### データ分離
- 企業ごとに完全なデータ分離
- 企業Aのユーザーは企業Bのデータにアクセス不可
- セッション管理でセキュアな認証

### パスワード保護
- bcryptによるパスワードハッシュ化
- セッショントークンによる認証
- 自動ログアウト機能

## 📊 企業ダッシュボード

各企業は以下の情報を管理画面で確認可能：

- ユーザー数
- アップロードファイル数
- 生成マニュアル数
- ストレージ使用量
- 最終活動日時

## 🔧 API エンドポイント

### 認証
- `POST /auth/login` - ログイン
- `POST /auth/logout` - ログアウト
- `GET /auth/status` - 認証状態確認

### ファイル管理
- `POST /upload` - ファイルアップロード
- `GET /files` - ファイル一覧
- `DELETE /files/{id}` - ファイル削除

### マニュアル生成
- `POST /generate_manual` - 基本マニュアル生成
- `GET /manuals` - マニュアル履歴
- `GET /download_manual/{id}` - マニュアルダウンロード

### 企業管理
- `GET /company/settings` - 企業設定取得
- `POST /company/settings` - 企業設定更新
- `GET /company/stats` - 企業統計

## 🔄 従来版からの移行

既存のmanual_generatorから移行する場合：

1. 既存データのバックアップ
2. 新バージョンのデータベース初期化
3. 企業作成
4. ファイルの再アップロード

```bash
# 既存ファイルを新企業フォルダにコピー
cp -r uploads/ uploads/company_sample001/
```

## 🛠️ 開発・デバッグ

### 開発モード起動

```bash
# デバッグモードで起動
FLASK_ENV=development python app_with_auth.py
```

### ログ確認

```bash
# アプリケーションログ
tail -f app.log

# データベースクエリログ（デバッグ時）
export SQLALCHEMY_ECHO=1
```

### テストデータ投入

```bash
# サンプルファイルとマニュアル作成
python test_data_generator.py
```

## 📈 本格運用時の推奨設定

### EC2インスタンス
- **t3.medium**以上（メモリ4GB+）
- **20GB+**のストレージ
- セキュリティグループでポート5000を開放

### データベース
- PostgreSQL 12+（高負荷時）
- 定期バックアップ設定
- 接続プール設定

### ファイル管理
- ローカルストレージ使用時は定期バックアップ
- S3使用時はライフサイクル管理
- ファイルサイズ制限の調整

### セキュリティ
- HTTPS化（Let's Encrypt推奨）
- ファイアウォール設定
- アクセスログ監視

## 🆘 トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   ```bash
   # データベース状態確認
   python db_manager.py list
   ```

2. **ファイルアップロードエラー**
   ```bash
   # アップロードディレクトリ権限確認
   ls -la uploads/
   chmod 755 uploads/
   ```

3. **認証エラー**
   ```bash
   # セッション情報クリア
   rm -rf flask_session/
   ```

### ログ確認

```bash
# アプリケーションエラー
grep ERROR app.log

# データベースエラー  
grep "sqlalchemy" app.log
```

## 📞 サポート

技術的な質問やサポートが必要な場合：

1. ログファイルの確認
2. エラーメッセージの記録
3. 再現手順の整理
4. システム環境の情報収集

---

**注意**: 本システムは製造業向けに最適化されていますが、他の業界でも活用可能です。企業の機密情報を取り扱う場合は、適切なセキュリティ対策を実施してください。
