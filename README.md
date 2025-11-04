# Manual Generator - 製造業向けAIマニュアル自動生成システム

動画からマニュアルを自動生成する高機能Webアプリケーション。Google Cloud Storage と Vertex AI (Gemini) を活用し、製造業の作業手順動画から構造化されたマニュアルを自動生成します。

## 🌐 本番環境

- **URL**: https://manual-generator.kantan-ai.net
- **デプロイ**: EC2 + Docker Compose + ALB + ACM + Route53
- **リージョン**: ap-northeast-1 (東京)

## 📋 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [主要機能](#主要機能)
3. [技術スタック](#技術スタック)
4. [システム仕様（MVP）](#システム仕様mvp)
5. [セットアップ手順](#セットアップ手順)
6. [ローカル開発](#ローカル開発)
7. [AWSデプロイ](#awsデプロイ)
8. [VS Codeタスク](#vs-codeタスク)
9. [トラブルシューティング](#トラブルシューティング)

---

## 🎯 プロジェクト概要

### 目的（MVP）
作業定義やテンプレート、動画から、現場で使える手順書（PDF/HTML）を半自動生成し、マニュアル作成・更新コストを削減します。

### リポジトリ構成
```
kantan-ai-manual-generator/
├── manual_generator/              # メインアプリケーション
│   ├── app.py                    # Flask API
│   ├── modules/                  # Gemini統合モジュール
│   ├── templates/                # HTMLテンプレート
│   ├── static/                   # 静的ファイル
│   └── README.md                 # アプリ詳細ドキュメント
├── infra/                        # インフラ設定
│   ├── DEPLOYMENT_AWS_ALB.md     # デプロイ手順
│   └── scripts/                  # デプロイスクリプト
├── scripts/                      # 一時スクリプト・分析ツール
├── .github/workflows/            # GitHub Actions
└── docker-compose.yml            # Docker構成
```

### 用語定義
- **工程/作業/手順**: 工程を構成する最小作業単位を「手順」と呼称
- **作業定義**: 手順の並び、所要時間、使用資材/工具、注意点などの構造化情報
- **テナント**: 企業ごとのデータ分離単位

---

## 🌟 主要機能

### 1. 📹 動画アップロード・管理
- **ドラッグ&ドロップ対応**: 直感的な動画ファイルのアップロード
- **クラウド直接アップロード**: Google Cloud Storage への直接アップロード
- **リアルタイムプレビュー**: 署名付きURLによる安全な動画プレビュー
- **対応形式**: MP4, AVI, MOV, MKV, WebM（最大2GB）

### 2. 🤖 AI マニュアル生成
- **Gemini AI 統合**: Google Gemini 2.5 Flash / 2.5 Pro
- **製造業特化プロンプト**: 作業手順の構造化された出力
- **比較分析**: 熟練者・非熟練者動画の同時分析
- **文書統合**: 見積書、図面、報告書のOCR処理

### 3. ⚙️ 高度なパラメータ制御
- **Geminiバージョン選択**: Flash（高速）/ Pro（高精度）
- **動的トークン制限**: バージョンに応じた自動調整
- **精密パラメータ調整**: Temperature、Top-P、出力トークン数
- **カスタムプロンプト**: ユースケース別の柔軟な設定

### 4. 🔐 企業認証機能
- **テナント機能**: 企業ごとのデータ分離
- **企業コード認証**: コード + パスワードによる認証
- **ストレージ選択**: ローカル / GCS / S3から選択可能
- **データ保存**: アップロード履歴、生成マニュアル、設定の管理

### 5. 🎨 洗練されたUI
- **レスポンシブデザイン**: デスクトップ・タブレット対応
- **リアルタイム同期**: パラメータ値の自動同期
- **視覚的フィードバック**: ローディング・エラー・成功メッセージ
- **Favicon対応**: Material Design準拠のアイコン

---

## 🔧 技術スタック

### バックエンド
- **Flask 3.0.0**: Python Webフレームワーク
- **SQLAlchemy**: ORM（SQLite/PostgreSQL/MySQL対応）
- **Google Cloud Storage**: スケーラブルファイルストレージ
- **Vertex AI**: Gemini モデルによるAI処理
- **bcrypt**: パスワードハッシュ化

### フロントエンド
- **HTML5/CSS3**: セマンティックマークアップ、Flexboxレイアウト
- **Vanilla JavaScript**: 軽量実装、Fetch API
- **Material Design**: 配色・アイコン

### インフラ
- **Docker + Docker Compose**: コンテナ化
- **AWS EC2**: アプリケーションホスティング
- **AWS ALB**: Application Load Balancer
- **AWS ACM**: SSL/TLS証明書管理
- **Route53**: DNSルーティング
- **GitHub Actions**: CI/CD自動デプロイ

### 開発ツール
- **VS Code**: 統合開発環境
- **GitHub Copilot**: AI支援コーディング
- **SERENA MCP**: コードナビゲーション

---

## 📐 システム仕様（MVP）

### スコープ
- **入力**: JSON/CSV作業定義、動画ファイル、画像ファイル
- **出力**: PDF/HTML手順書（A4縦想定・1カラム/2カラム）
- **ターゲット**: 単一作業の手順書（多品種展開はテンプレート差し替え）

### ユースケース
1. 企業コードでログイン
2. 動画ファイルをアップロード
3. Geminiバージョン・パラメータを選択
4. プロンプトをカスタマイズ（任意）
5. マニュアル生成実行
6. プレビュー確認
7. PDF/HTMLとしてエクスポート

### 機能要件
- **F1**: 作業定義の取り込み（JSON/CSV→内部モデル）
- **F2**: テンプレート適用（動的HTML生成）
- **F3**: 画像取込・リサイズ・キャプション
- **F4**: 目次・自動番号付与・注意/警告表示
- **F5**: PDF生成（ヘッダ/フッタ、ページ番号）
- **F6**: 設定の保存/読込（企業別）
- **F7**: AI動画分析（Gemini統合）
- **F8**: 企業認証・データ分離

### 非機能要件
- **N1**: クラウドベース（GCS連携）
- **N2**: 20手順・画像10枚程度で2分以内に生成
- **N3**: 再現性（テンプレート+データで同一結果）
- **N4**: セキュアな認証（bcryptハッシュ化）
- **N5**: 企業間データ完全分離

### データモデル
```python
Manual {
    id: string,
    title: string,
    description: string,
    version: string,
    company_id: string,
    created_by: string,
    created_at: datetime,
    updated_at: datetime,
    stage1_content: json,      # Gemini分析結果
    stage2_content: json,      # フレーム抽出結果
    stage3_content: text,      # HTML生成結果
    generation_status: string,
    generation_progress: int,
    error_message: string
}

Company {
    id: string,
    code: string (unique),
    name: string,
    password_hash: string,
    storage_type: string,      # local/gcs/s3
    created_at: datetime
}

User {
    id: string,
    username: string,
    company_id: string,
    role: string,
    created_at: datetime
}
```

### KPI/評価指標
- **マニュアル作成時間**: 70%短縮（20時間→6時間）
- **動画アップロード→PDF出力**: 5分以内
- **用語統一率**: 95%以上
- **動作認識精度**: 95%以上
- **レイアウト崩れ**: 最小化

### 受け入れ条件
- サンプル動画から、Gemini分析でPDF/HTMLを生成できる
- 企業認証・データ分離が機能する
- 設定の保存/読込が機能する
- GitHub Actionsで自動デプロイできる

---

## 🚀 セットアップ手順

### 前提条件
- Python 3.8+
- Google Cloud Project（Vertex AI, Cloud Storage有効）
- Google Cloud 認証情報（サービスアカウントキー）
- Docker + Docker Compose（本番デプロイ時）

### 1. リポジトリクローン
```bash
git clone https://github.com/nextam/kantan-ai-manual-generator.git
cd kantan-ai-manual-generator
```

### 2. 依存関係インストール
```bash
cd manual_generator
pip install -r requirements.txt
```

### 3. Google Cloud 設定

#### 認証ファイル配置
```bash
# gcp-credentials.json を manual_generator/ に配置
cp /path/to/your/credentials.json manual_generator/gcp-credentials.json
```

#### Cloud Storage バケット作成
```bash
# Google Cloud CLI でバケット作成
gsutil mb gs://manual_generator

# 権限設定
gsutil iam ch serviceAccount:your-service-account@project.iam.gserviceaccount.com:objectAdmin gs://manual_generator
```

#### 必要なAPI有効化
```bash
# Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Cloud Storage API
gcloud services enable storage.googleapis.com
```

### 4. 環境変数設定
`.env.example` をコピーして `.env` を作成し、必要最小限の設定を行います：

```bash
cp .env.example .env
```

**推奨設定: サービスアカウント認証（本番環境）**

```env
# ============================================
# 必須: Google Cloud認証（サービスアカウント）
# ============================================
GOOGLE_APPLICATION_CREDENTIALS="gcp-credentials.json"

# ============================================
# 必須: Google Cloud Storage Bucket
# ============================================
GCS_BUCKET_NAME="your-gcs-bucket-name"

# ============================================
# 必須: Application Secret Key
# ============================================
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY="your-random-secret-key-here"
```

**セキュリティ上の重要なポイント**:

| 認証方式 | セキュリティ | 推奨環境 | 理由 |
|---------|-------------|---------|------|
| **サービスアカウント** | ✅ **高** | **本番環境推奨** | IAMで細かい権限制御、監査ログ完備、自動ローテーション可能 |
| API Key | ⚠️ 低 | 開発・テストのみ | プロジェクト全体の権限、監査機能限定的 |

**認証方式の選択**:
- ✅ **本番環境**: サービスアカウント認証（`gcp-credentials.json`）を使用
- ⚠️ **開発環境のみ**: API Key認証（非推奨、レガシー）

**サービスアカウントの作成方法**:
```bash
# 1. サービスアカウント作成
gcloud iam service-accounts create manual-generator \
    --display-name="Manual Generator Service Account"

# 2. 必要な権限を付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# 3. キーファイル生成
gcloud iam service-accounts keys create gcp-credentials.json \
    --iam-account=manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

**オプション設定** (設定しない場合は自動検出またはデフォルト値を使用):

```env
# Google Cloud Project ID
# 省略可: gcp-credentials.json から自動読み込み
# PROJECT_ID="your-gcp-project-id"

# Vertex AI Location
# デフォルト: us-central1
# VERTEX_AI_LOCATION="asia-northeast1"

# Support Email
# SUPPORT_EMAIL="support@your-domain.com"

# Environment
# FLASK_ENV="production"
# DEBUG="False"
```

**自動検出される項目**:
- ✅ `PROJECT_ID`: `gcp-credentials.json`から自動的に読み込まれます
- ✅ `GOOGLE_CLOUD_PROJECT_ID`: 不要（PROJECT_IDと同じ）
- ✅ その他の設定: デフォルト値が設定されているため省略可能

**レガシーAPI Key認証（非推奨）**:
```env
# ⚠️ WARNING: セキュリティリスクあり、本番環境では使用しないでください
# GOOGLE_API_KEY="your-api-key-here"
```

### 5. データベース初期化
```bash
cd manual_generator
python db_manager.py init
```

サンプル企業が自動作成されます：
- **企業1**: サンプル製造業株式会社 (コード: `sample001`, パスワード: `password123`)
- **企業2**: テスト工業有限会社 (コード: `test002`, パスワード: `test123456`)

### 6. アプリケーション起動

#### Windows
```bash
cd manual_generator
start.bat
```

#### Linux/Mac
```bash
cd manual_generator
chmod +x start.sh
./start.sh
```

#### 直接起動
```bash
python app.py
```

### 7. ブラウザでアクセス
http://localhost:5000

---

## 💻 ローカル開発

### VS Code タスク

このプロジェクトには効率的な開発用タスクが設定されています。

#### 利用可能なタスク

| タスク名 | 説明 | ポート |
|---------|------|--------|
| **すべてのローカルサーバーを停止** | すべてのローカルサーバーを停止 | - |
| **マニュアル生成サーバー起動 (ポート5000)** | Waitressで起動 | 5000 |
| **サーバー状態確認** | サーバー動作状態確認 | - |
| **マニュアル生成をブラウザで開く** | http://localhost:5000を開く | - |

#### タスク実行方法
1. **Ctrl + Shift + P** でコマンドパレット
2. **"Tasks: Run Task"** を選択
3. 実行したいタスクを選択

#### おすすめワークフロー

**初回起動:**
```
1. "マニュアル生成サーバー起動 (ポート5000)"
2. "サーバー状態確認"
3. "マニュアル生成をブラウザで開く"
```

**開発中の再起動:**
```
1. "すべてのローカルサーバーを停止"
2. 数秒待機
3. "マニュアル生成サーバー起動 (ポート5000)"
```

### 開発用データベース管理
```bash
# 企業作成
python db_manager.py create

# 企業一覧
python db_manager.py list

# バックアップ
python db_manager.py backup

# 孤立ファイル清掃
python db_manager.py clean
```

### デバッグモード
```bash
# .env で設定
FLASK_ENV=development

# または直接起動
FLASK_ENV=development python app.py
```

---

## ☁️ AWSデプロイ

### アーキテクチャ概要

```
Internet
    ↓
Route53 (manual-generator.kantan-ai.net)
    ↓
Application Load Balancer (ALB)
    ↓ HTTPS:443 → HTTP:8080
EC2 Instance (Amazon Linux 2)
    ↓
Docker Compose
    ↓
Manual Generator Container (Flask:5000)
```

### デプロイ構成
- **ドメイン**: kantan-ai.net (Route53)
- **サブドメイン**: manual-generator.kantan-ai.net
- **証明書**: ACM (arn:aws:acm:ap-northeast-1:442042524629:certificate/ad7baf4e-7cec-4b3a-8d09-a73363098de3)
- **リージョン**: ap-northeast-1 (東京)
- **EC2**: t3.medium以上推奨
- **ストレージ**: 20GB以上

### 1. EC2準備

#### OS・Docker セットアップ
```bash
# EC2にSSH接続
ssh -i "kantan-ai.pem" ec2-user@ec2-52-198-123-171.ap-northeast-1.compute.amazonaws.com

# システム更新
sudo yum update -y

# Docker インストール
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ec2-user
sudo systemctl enable --now docker

# Docker Compose v2 インストール
sudo curl -L "https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# プロジェクト配置
sudo mkdir -p /opt/kantan-ai-manual-generator
sudo chown ec2-user:ec2-user /opt/kantan-ai-manual-generator
cd /opt/kantan-ai-manual-generator
git clone https://github.com/nextam/kantan-ai-manual-generator.git .
```

#### セキュリティグループ設定
- **インバウンド**:
  - 8080/TCP: ALBのセキュリティグループからのみ
  - 22/TCP: 管理者固定IPからのみ
- **アウトバウンド**: すべて許可

### 2. 環境変数設定
```bash
cd /opt/kantan-ai-manual-generator/manual_generator
nano .env
# 本番用の値を設定（GCS認証情報等）
```

### 3. Docker Compose 起動
```bash
cd /opt/kantan-ai-manual-generator
sudo docker-compose build
sudo docker-compose up -d

# 動作確認
curl -s http://127.0.0.1:8080/ | head -n 1
```

### 4. ALB設定

#### ターゲットグループ作成
- **Protocol**: HTTP
- **Port**: 8080
- **Health Check Path**: `/`
- **ターゲット**: EC2インスタンス

#### ALBリスナー設定
- **443 (HTTPS)**:
  - 証明書: ACM証明書選択
  - ルール: Host header `manual-generator.kantan-ai.net` → ターゲットグループ転送
- **80 (HTTP)**:
  - ルール: すべて HTTPS(443) にリダイレクト

### 5. Route53設定
- **レコードタイプ**: A (ALIAS)
- **名前**: manual-generator.kantan-ai.net
- **値**: ALBのDNS名

### 6. GitHub Actions 自動デプロイ

#### GitHub Secrets 設定
1. GitHubリポジトリ → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**
3. **Name**: `EC2_PRIVATE_KEY`
4. **Secret**: kantan-ai.pem の内容全体をコピー&ペースト

#### 自動デプロイの動作
- **トリガー**: mainブランチへのpush
- **ワークフロー**: `.github/workflows/deploy-ec2.yml`
- **処理フロー**:
  1. 変更検知（manual_generator/, docker-compose.yml, infra/）
  2. Docker イメージビルド（変更時のみ）
  3. EC2へSSH接続
  4. rsync増分同期
  5. サービス再起動（変更時のみ）
  6. ヘルスチェック確認

#### デプロイ時間短縮効果

| 項目 | 従来 | 最適化後 | 短縮率 |
|------|------|----------|--------|
| Docker build | 3-5分 | 1-2分 | 60-70% |
| ファイル転送 | 30-60秒 | 5-15秒 | 70-80% |
| サービス再起動 | 60-90秒 | 30-45秒 | 50% |
| **合計** | **5-7分** | **2-3分** | **50-60%** |

#### ログ確認
```bash
# GitHub Actions
リポジトリ → Actions → Auto Deploy to EC2 → 詳細ログ

# EC2コンテナログ
sudo docker-compose logs -f manual
```

#### 手動デプロイ（緊急時）
```bash
ssh -i "kantan-ai.pem" ec2-user@ec2-52-198-123-171.ap-northeast-1.compute.amazonaws.com
cd /opt/kantan-ai-manual-generator
git pull origin main
sudo docker-compose build manual
sudo docker-compose up -d manual
sudo docker-compose logs -f manual
```

---

## 🛠️ トラブルシューティング

### よくある問題

#### 1. 認証エラー
```bash
# 問題: "Your default credentials were not found"
# 解決: 認証ファイルパス確認
export GOOGLE_APPLICATION_CREDENTIALS="/full/path/to/gcp-credentials.json"

# サービスアカウントキー確認
gcloud auth application-default print-access-token
```

#### 2. ファイルアップロードエラー
```bash
# 問題: GCS アップロード失敗
# 解決: バケット権限確認
gsutil iam get gs://manual_generator

# 必要権限: Storage Object Admin
```

#### 3. Gemini API エラー
```bash
# 問題: Vertex AI API エラー
# 解決: API有効化確認
gcloud services list --enabled | grep aiplatform

# リージョン確認
gcloud config get-value compute/region
```

#### 4. ポート競合
```bash
# Windows
# VS Codeタスク: "すべてのローカルサーバーを停止"

# Linux/Mac
sudo lsof -i :5000
kill -9 <PID>
```

#### 5. Docker コンテナ起動失敗
```bash
# ログ確認
sudo docker-compose logs manual

# コンテナ再起動
sudo docker-compose restart manual

# 完全再ビルド
sudo docker-compose down
sudo docker-compose build --no-cache
sudo docker-compose up -d
```

#### 6. データベースエラー
```bash
# データベース状態確認
python db_manager.py list

# バックアップから復元
cp instance/manual_generator.db.backup_YYYYMMDD instance/manual_generator.db
```

#### 7. GitHub Actions デプロイ失敗

**SSH接続エラー:**
```
Permission denied (publickey)
```
→ `EC2_PRIVATE_KEY` Secret確認

**Docker build失敗:**
```
ERROR: failed to solve
```
→ requirements.txt依存関係確認

**Health check失敗:**
```
❌ Manual health check failed
```
→ EC2でコンテナログ確認: `sudo docker-compose logs manual`

### ログ確認方法

#### ローカル開発
```bash
# アプリケーションログ
tail -f manual_generator/app.log

# Flask デバッグログ
FLASK_ENV=development python app.py
```

#### 本番環境（EC2）
```bash
# Docker コンテナログ
sudo docker-compose logs -f manual

# エラーのみ
sudo docker-compose logs manual | grep -i error

# 最新100行
sudo docker-compose logs --tail=100 manual
```

---

## 📊 システム要件

### 最小要件
- **CPU**: 2コア以上
- **RAM**: 4GB以上
- **ストレージ**: 10GB以上
- **ネットワーク**: 安定したインターネット接続

### 推奨要件（本番）
- **CPU**: 4コア以上
- **RAM**: 8GB以上
- **ストレージ**: SSD 20GB以上
- **帯域**: 100Mbps以上

---

## 🔒 セキュリティ

### データ保護
- **パスワード**: bcryptハッシュ化
- **セッション**: セキュアなトークン管理
- **データ分離**: 企業間の完全隔離
- **HTTPS**: ALB + ACM証明書

### 認証情報管理
- **ローカル**: `.env` ファイル（.gitignore済み）
- **本番**: AWS Secrets Manager / Parameter Store推奨
- **GCS認証**: サービスアカウントキー（ボリュームマウント推奨）

### ベストプラクティス
- 定期的なパスワード変更
- アクセスログ監視
- 定期的なデータバックアップ
- 最小権限の原則

---

## 📈 今後の拡張

### 機能拡張
- **多言語対応**: i18n による国際化
- **バッチ処理**: 複数動画の一括処理
- **結果エクスポート**: PDF・Word形式
- **ユーザー認証**: 企業内ロール管理
- **履歴管理**: バージョン管理・差分表示

### インフラ拡張
- **Auto Scaling**: ECS/Fargate 移行
- **CloudWatch**: 監視・アラート設定
- **RDS**: PostgreSQL移行（高負荷時）
- **CDN**: CloudFront導入

### API拡張
- **REST API**: プログラマティックアクセス
- **Webhook**: 処理完了通知
- **統合**: 他システムとのAPI連携

---

## 📞 サポート・連絡先

### GitHub
- **Issues**: バグレポート・機能要望
- **Pull Requests**: コントリビューション歓迎
- **Discussions**: 質問・アイデア共有

### ドキュメント
- **manual_generator/README.md**: アプリケーション詳細
- **manual_generator/GEMINI_ENHANCED_SPECIFICATION.md**: Gemini技術仕様
- **.github/copilot-instructions.md**: 開発ガイドライン

---

## 📄 ライセンス

このプロジェクトのライセンスは社内/委託条件に準じます。

### 依存関係ライセンス
- Flask: BSD-3-Clause
- Google Cloud SDK: Apache 2.0
- その他: 各パッケージのライセンスに準拠

---

**Manual Generator** - 製造業の未来を支えるAI駆動マニュアル自動生成システム

**Version**: 1.0  
**Last Updated**: 2025年11月5日