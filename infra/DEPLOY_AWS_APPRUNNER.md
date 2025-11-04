# AWS App Runner デプロイガイド - Operation Analysis

このガイドでは、Operation Analysis アプリケーションをAWS App Runnerにデプロイする手順を説明します。

## 🎯 概要

AWS App Runnerは、コンテナ化されたWebアプリケーションやAPIサービスを簡単にデプロイできるフルマネージドサービスです。Operation Analysisアプリケーションを以下の構成でデプロイします：

- **コンテナレジストリ**: Amazon ECR
- **インスタンス仕様**: 1 vCPU, 2 GB RAM
- **ポート**: 5000
- **自動デプロイ**: GitHub Actions連携

## 📋 前提条件

### 必要なツール
1. **AWS CLI**: [インストールガイド](https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/getting-started-install.html)
2. **Docker**: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
3. **Git**: バージョン管理用

### AWS権限
以下の権限を持つIAMユーザーまたはロールが必要です：
- `AmazonAppRunnerFullAccess`
- `AmazonEC2ContainerRegistryFullAccess`
- `IAMFullAccess`（ロール作成用）
- `SecretsManagerReadWrite`（オプション）

## 🚀 デプロイ手順

### Step 1: AWS CLI設定
```powershell
# AWS CLI設定（初回のみ）
aws configure
# AWS Access Key ID: [あなたのアクセスキー]
# AWS Secret Access Key: [あなたのシークレットキー]
# Default region name: ap-northeast-1
# Default output format: json
```

### Step 2: AWSリソース作成

#### 2.1 ECRリポジトリ作成
```powershell
aws ecr create-repository --repository-name operation-analysis --region ap-northeast-1
```

#### 2.2 IAMロール作成

**App Runner Service Role:**
```powershell
# Trust policy作成
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@ | Out-File -FilePath "apprunner-service-role-trust.json" -Encoding utf8

# ロール作成
aws iam create-role --role-name AppRunnerServiceRole --assume-role-policy-document file://apprunner-service-role-trust.json

# ポリシーアタッチ
aws iam attach-role-policy --role-name AppRunnerServiceRole --policy-arn arn:aws:iam::aws:policy/service-role/AppRunnerServicePolicyForECRAccess
```

**App Runner Task Role（アプリケーション用）:**
```powershell
# Task Role Trust policy
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "tasks.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@ | Out-File -FilePath "apprunner-task-role-trust.json" -Encoding utf8

# Task Role作成
aws iam create-role --role-name AppRunnerTaskRole --assume-role-policy-document file://apprunner-task-role-trust.json
```

### Step 3: 手動デプロイ（GitHub Actions使用前のテスト）

#### 3.1 operation_analysisディレクトリに移動
```powershell
cd c:\Users\suusa\OneDrive\Documents\GitHub\chuden-demoapp\operation_analysis
```

#### 3.2 ECRログインとイメージビルド
```powershell
# ECRログイン
$AccountId = aws sts get-caller-identity --query Account --output text
$Region = "ap-northeast-1"
$ECRUri = "$AccountId.dkr.ecr.$Region.amazonaws.com"

aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ECRUri

# Dockerイメージビルド
docker build -f Dockerfile.apprunner -t "$ECRUri/operation-analysis:latest" .

# ECRにプッシュ
docker push "$ECRUri/operation-analysis:latest"
```

#### 3.3 App Runnerサービス作成
```powershell
# サービス設定ファイル作成
@"
{
  "ServiceName": "operation-analysis-app",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "$ECRUri/operation-analysis:latest",
      "ImageConfiguration": {
        "Port": "5000",
        "RuntimeEnvironmentVariables": {
          "MODEL_CACHE_DIR": "/app/model_cache",
          "GCS_BUCKET_NAME": "operation_analysis_model",
          "PROJECT_ID": "career-survival",
          "PORT": "5000",
          "FLASK_ENV": "production"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": true
  },
  "InstanceConfiguration": {
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }
}
"@ | Out-File -FilePath "apprunner-config.json" -Encoding utf8

# App Runnerサービス作成
aws apprunner create-service --cli-input-json file://apprunner-config.json
```

#### 3.4 デプロイ完了確認
```powershell
# サービス状態確認
aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`operation-analysis-app`]'

# サービスURL取得
$ServiceArn = aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`operation-analysis-app`].ServiceArn' --output text
$ServiceUrl = aws apprunner describe-service --service-arn $ServiceArn --query 'Service.ServiceUrl' --output text

Write-Host "🎉 デプロイ完了！"
Write-Host "App URL: https://$ServiceUrl"
Write-Host "Health Check: https://$ServiceUrl/health"
```

### Step 4: GitHub Actions自動デプロイ設定

#### 4.1 GitHubシークレット設定
GitHubリポジトリの Settings > Secrets and variables > Actions で以下を設定：

- `AWS_ACCESS_KEY_ID`: AWSアクセスキーID
- `AWS_SECRET_ACCESS_KEY`: AWSシークレットアクセスキー

#### 4.2 GitHub Actionsワークフロー
既に `.github/workflows/deploy-operation-analysis-apprunner.yml` が作成されています。

#### 4.3 自動デプロイトリガー
```bash
# mainブランチにプッシュで自動デプロイ
git add .
git commit -m "Add AWS App Runner deployment configuration"
git push origin main
```

## 🔧 運用管理

### デプロイ状況確認
```powershell
# App Runnerサービス一覧
aws apprunner list-services

# 特定サービスの詳細
aws apprunner describe-service --service-arn [SERVICE_ARN]

# デプロイメント履歴
aws apprunner list-operations --service-arn [SERVICE_ARN]
```

### ログ確認
AWS CloudWatch Logsで確認：
- ロググループ: `/aws/apprunner/operation-analysis-app/[SERVICE_ID]/application`

### スケーリング設定
```powershell
# Auto Scaling設定（オプション）
aws apprunner update-service --service-arn [SERVICE_ARN] --auto-scaling-configuration-arn [AUTO_SCALING_CONFIG_ARN]
```

## 💰 コスト最適化

### インスタンス仕様調整
```json
{
  "InstanceConfiguration": {
    "Cpu": "0.25 vCPU",  // より小さなインスタンス
    "Memory": "0.5 GB"
  }
}
```

### 自動停止設定
App Runnerは使用量ベース課金のため、トラフィックがない場合は自動的に停止します。

## 🚨 トラブルシューティング

### よくある問題

#### 1. ECRプッシュエラー
```powershell
# ECR認証確認
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin $ECRUri
```

#### 2. App Runnerサービス作成失敗
```powershell
# IAMロール確認
aws iam get-role --role-name AppRunnerServiceRole
aws iam get-role --role-name AppRunnerTaskRole
```

#### 3. Health Check失敗
- `/health` エンドポイントが正しく応答するか確認
- ポート設定（5000）が正しいか確認

### デバッグコマンド
```powershell
# ローカルでテスト
docker run -p 5000:5000 [IMAGE_NAME]

# Health Check テスト
curl http://localhost:5000/health
```

## 📚 参考資料

- [AWS App Runner公式ドキュメント](https://docs.aws.amazon.com/apprunner/)
- [App Runner料金](https://aws.amazon.com/jp/apprunner/pricing/)
- [ECR使用方法](https://docs.aws.amazon.com/ecr/)

---

このガイドに従って、Operation AnalysisアプリケーションをAWS App Runnerに正常にデプロイできます。問題が発生した場合は、トラブルシューティングセクションを参照してください。
