# AWS デプロイ設計 (1台の EC2 + docker-compose + ALB/ACM/Route53)

このドキュメントは、2つの Flask アプリ (Manual Generator / Operation Analysis) を1台の EC2 インスタンス上で docker-compose により稼働させ、外部公開は Application Load Balancer(ALB) でホストベースルーティングし、ACM 証明書で HTTPS 化する手順です。

- ドメイン: kantan-ai.net (Route53)
- 証明書(ACM): arn:aws:acm:ap-northeast-1:442042524629:certificate/ad7baf4e-7cec-4b3a-8d09-a73363098de3
- リージョン: ap-northeast-1 (東京)

## 構成概要

- EC2 上で以下の 2 サービスを起動
  - manual: Flask on port 5000 (外部 8080 に公開, ただし ALB から到達するのは EC2 の 8080)
  - analysis: Flask on port 5000 (外部 8081 に公開, 同上 8081)
- ALB で HTTPS(443) を終端し、Host ヘッダで 2 つのターゲットグループにルーティング
  - manual-generator.kantan-ai.net → EC2:8080
  - operation-analysis.kantan-ai.net → EC2:8081
- Route53 で A レコード(ALIAS) を ALB に向ける

## 1. EC2 準備

- OS: Amazon Linux 2 または最新の Amazon Linux 2023 を推奨
- セキュリティグループ(SG) 設定
  - インバウンド: 80/TCP, 443/TCP (ALB 用) は ALB の SG のみ許可
  - 8080/TCP, 8081/TCP は ALB からのトラフィックのみ許可
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
curl -s http://127.0.0.1:8081/health
```

- manual: http://<EC2-private-ip>:8080/
- analysis: http://<EC2-private-ip>:8081/

## 4. ALB 作成

1) ALB を作成 (インターネット向け / IPv4)
- リスナー: 443(HTTPS) を追加、ACM 証明書は指定の ARN を選択
- オプションで 80(HTTP) も作成し、HTTP→HTTPS リダイレクトルールを設定

2) ターゲットグループ(TG) を 2 つ作成
- TG1: protocol HTTP, port 8080, health check path: `/` (manual)
- TG2: protocol HTTP, port 8081, health check path: `/health` (analysis) 既に実装済
- ターゲットに EC2 を登録

3) リスナールール
- 443 リスナーにルール追加:
  - IF Host header is `manual-generator.kantan-ai.net` → forward to TG1
  - IF Host header is `operation-analysis.kantan-ai.net` → forward to TG2
  - デフォルトは 404 か任意の固定レスポンス

4) 80 リスナー(任意)
- ルール: すべて HTTPS(443) にリダイレクト

## 5. Route53 設定

- `manual-generator.kantan-ai.net` A レコード(ALIAS) → ALB の DNS 名
- `operation-analysis.kantan-ai.net` A レコード(ALIAS) → 同 ALB

ACM 証明書は SAN に `manual-generator.kantan-ai.net` と `operation-analysis.kantan-ai.net` を含む必要があります。証明書 ARN がすでにマルチドメインであればそのまま利用できます。未登録なら ACM で追加作成/検証してください。

## 6. セキュリティ/運用メモ

- EC2 SG は ALB SG のみを許可 (8080/8081)
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

以上で、1台の EC2 上に 2 つの Flask アプリを docker-compose で稼働させ、ALB + ACM で HTTPS 公開し、Route53 でサブドメイン割当する構成が完成します。
