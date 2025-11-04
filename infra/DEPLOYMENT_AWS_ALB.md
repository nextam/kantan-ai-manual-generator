# AWS デプロイ設計 (EC2 + docker-compose + ALB/ACM/Route53)

このドキュメントは、Manual Generator Flask アプリを EC2 インスタンス上で docker-compose により稼働させ、外部公開は Application Load Balancer(ALB) でルーティングし、ACM 証明書で HTTPS 化する手順です。

- ドメイン: kantan-ai.net (Route53)
- 証明書(ACM): arn:aws:acm:ap-northeast-1:442042524629:certificate/ad7baf4e-7cec-4b3a-8d09-a73363098de3
- リージョン: ap-northeast-1 (東京)

## 構成概要

- EC2 上で Manual Generator サービスを起動
  - manual: Flask on port 5000 (外部 8080 に公開, ただし ALB から到達するのは EC2 の 8080)
- ALB で HTTPS(443) を終端し、Host ヘッダでターゲットグループにルーティング
  - manual-generator.kantan-ai.net → EC2:8080
- Route53 で A レコード(ALIAS) を ALB に向ける

## 1. EC2 準備

- OS: Amazon Linux 2 または最新の Amazon Linux 2023 を推奨
- セキュリティグループ(SG) 設定
  - インバウンド: 80/TCP, 443/TCP (ALB 用) は ALB の SG のみ許可
  - 8080/TCP は ALB からのトラフィックのみ許可
  - SSH(22/TCP) は管理者の固定IPからのみ
- IAM ロール: CloudWatch Logs 等が必要なら付与（必須ではない）

EC2 に Docker と docker-compose をセットアップし、リポジトリを配置:

```
# EC2 上で (例)
sudo yum update -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ec2-user
sudo systemctl enable --now docker

# docker compose v2
sudo curl -L "https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# コード配置 (例: /opt/kantan-ai-manual-generator)
sudo mkdir -p /opt/kantan-ai-manual-generator
sudo chown ec2-user:ec2-user /opt/kantan-ai-manual-generator
# リポジトリを git clone or scp で配置
```

## 2. アプリの環境変数

Manual Generator は Google Cloud 認証や API キーが必要です。`.env` を `manual_generator/.env` に配置してください。

例 (`manual_generator/.env`):

```
GOOGLE_API_KEY=your_google_api_key
GCS_BUCKET_NAME=manual_generator
PROJECT_ID=career-survival
```

`gcp-credentials.json` は手元の資格情報を含むため、秘匿管理してください。EC2 に配置する場合は SSM Parameter Store や Secrets Manager の利用を推奨。今回は簡易化のためビルドコンテキストに含めていますが、本番では避け、起動時にボリュームマウント等に置き換えてください。

## 3. docker-compose 起動

EC2 で以下を実行:

```
cd /opt/kantan-ai-manual-generator
# docker-compose.yml がある場所
sudo docker-compose pull || true
sudo docker-compose build
sudo docker-compose up -d

# 動作確認 (EC2 内部)
curl -s http://127.0.0.1:8080/ | head -n 1
```

- manual: http://<EC2-private-ip>:8080/

## 4. ALB 作成

1) ALB を作成 (インターネット向け / IPv4)
- リスナー: 443(HTTPS) を追加、ACM 証明書は指定の ARN を選択
- オプションで 80(HTTP) も作成し、HTTP→HTTPS リダイレクトルールを設定

2) ターゲットグループ(TG) を作成
- TG: protocol HTTP, port 8080, health check path: `/` (manual)
- ターゲットに EC2 を登録

3) リスナールール
- 443 リスナーにルール追加:
  - IF Host header is `manual-generator.kantan-ai.net` → forward to TG
  - デフォルトは 404 か任意の固定レスポンス

4) 80 リスナー(任意)
- ルール: すべて HTTPS(443) にリダイレクト

## 5. Route53 設定

- `manual-generator.kantan-ai.net` A レコード(ALIAS) → ALB の DNS 名

ACM 証明書は SAN に `manual-generator.kantan-ai.net` を含む必要があります。証明書 ARN がすでに設定されていればそのまま利用できます。未登録なら ACM で追加作成/検証してください。

## 6. セキュリティ/運用メモ

---

## 7. GitHub Actions 自動デプロイ

### GitHub Secrets設定

#### EC2_PRIVATE_KEY の設定
1. GitHubリポジトリ → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック
3. 設定：
   - **Name**: `EC2_PRIVATE_KEY`
   - **Secret**: EC2プライベートキー（kantan-ai.pem）の内容全体

```bash
# プライベートキーの内容確認
cat kantan-ai.pem
```

### 自動デプロイの動作
- **トリガー**: mainブランチへのpush
- **ワークフロー**: `.github/workflows/deploy-ec2.yml`
- **処理内容**:
  1. 変更検知（manual_generator/, docker-compose.yml, infra/）
  2. Docker イメージビルド（変更があった場合のみ）
  3. EC2へのSSH接続
  4. ファイル転送（rsync増分同期）
  5. サービス再起動（変更があった場合のみ）
  6. ヘルスチェック確認

### デプロイ最適化の効果

#### 変更検知システム
- manual_generator関連の変更を検知
- docker-compose.yml変更を検知
- 変更がない場合はスキップ

#### ビルド・デプロイ時間短縮
| 項目 | 従来 | 最適化後 | 短縮効果 |
|------|------|----------|----------|
| Docker build | 3-5分 | 1-2分 | 60-70% |
| ファイル転送 | 30-60秒 | 5-15秒 | 70-80% |
| サービス再起動 | 60-90秒 | 30-45秒 | 50% |
| **合計** | **5-7分** | **2-3分** | **50-60%** |

### GitHub Actions ログ確認
1. リポジトリの **Actions** タブ
2. **Auto Deploy to EC2** ワークフロー選択
3. 各ステップの詳細ログを確認

### よく見るログ出力
```bash
# 変更検知結果
✅ Manual Generator changes: true

# ビルド実行
🔨 Building manual service...

# デプロイ実行
🚀 Starting deployment...
📦 Transferring manual image...
⏹️ Stopping manual...
🚀 Starting services...
✅ Deployment completed successfully!
```

### トラブルシューティング

#### SSH接続エラー
```
Permission denied (publickey)
```
→ `EC2_PRIVATE_KEY` Secretが正しく設定されているか確認

#### Docker build失敗
```
ERROR: failed to solve: process "/bin/sh -c pip install" did not complete
```
→ requirements.txtの内容確認、依存関係の競合解決

#### Health check失敗
```
❌ Manual health check failed
```
→ EC2上でコンテナログ確認: `sudo docker-compose logs manual`

### 手動デプロイコマンド
緊急時やテスト時は手動でもデプロイ可能：

```bash
# EC2に直接SSH接続
ssh -i "kantan-ai.pem" ec2-user@ec2-52-198-123-171.ap-northeast-1.compute.amazonaws.com

# 最新コードを取得
cd /opt/kantan-ai-manual-generator
git pull origin main

# イメージビルドとサービス再起動
sudo docker-compose build manual
sudo docker-compose up -d manual

# ログ確認
sudo docker-compose logs -f manual
```

---

- EC2 SG は ALB SG のみを許可 (8080)
- アプリログはコンテナログとして CloudWatch Logs (awslogs) ドライバに変更可
- 資格情報は Secrets Manager/Parameter Store に移行推奨
- Auto-healing: ターゲットグループのヘルスチェックで NG になれば ALB が切替
- スケールアウトが必要なら ECS/Fargate 移行を検討

## 7. トラブルシューティング

- 502/504: ヘルスチェック失敗または SG/ポート誤り
- 404: リスナールールの Host 条件と DNS 名の不一致
- 403(ACM): ALB で証明書リージョン/ARN が不一致
- Manual Generator の GCP 設定不備: `/upload` で認証エラー。`.env` や JSON を確認

---

以上で、EC2 上に Manual Generator を docker-compose で稼働させ、ALB + ACM で HTTPS 公開し、Route53 でサブドメイン割当する構成が完成します。
