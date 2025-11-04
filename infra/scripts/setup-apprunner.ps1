# AWS App Runner デプロイ用セットアップスクリプト
param(
    [Parameter(Mandatory=$true)]
    [string]$AWSProfile = "default",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "ap-northeast-1",
    
    [Parameter(Mandatory=$false)]
    [string]$AppName = "operation-analysis-app",
    
    [Parameter(Mandatory=$false)]
    [string]$ECRRepository = "operation-analysis"
)

Write-Host "🚀 AWS App Runner セットアップを開始します" -ForegroundColor Green

# AWS CLI設定確認
Write-Host "📋 AWS CLI設定確認中..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --profile $AWSProfile | ConvertFrom-Json
    Write-Host "✅ AWS認証確認: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS認証に失敗しました。aws configure --profile $AWSProfile を実行してください" -ForegroundColor Red
    exit 1
}

# ECRリポジトリ作成
Write-Host "📦 ECRリポジトリを作成中..." -ForegroundColor Yellow
try {
    aws ecr create-repository --repository-name $ECRRepository --region $Region --profile $AWSProfile | Out-Null
    Write-Host "✅ ECRリポジトリ '$ECRRepository' を作成しました" -ForegroundColor Green
} catch {
    Write-Host "⚠️ ECRリポジトリ '$ECRRepository' は既に存在します" -ForegroundColor Yellow
}

# ECRリポジトリURIを取得
$ecrUri = aws ecr describe-repositories --repository-names $ECRRepository --region $Region --profile $AWSProfile --query 'repositories[0].repositoryUri' --output text
Write-Host "📝 ECRリポジトリURI: $ecrUri" -ForegroundColor Cyan

# App Runner IAMロール作成
Write-Host "🔐 App Runner用IAMロールを作成中..." -ForegroundColor Yellow

# App Runner Service Role
$appRunnerServiceRolePolicy = @"
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
"@

$appRunnerServiceRolePolicy | Out-File -FilePath "apprunner-service-role-trust.json" -Encoding utf8

# App Runner Task Role (アプリケーションが使用するロール)
$appRunnerTaskRolePolicy = @"
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
"@

$appRunnerTaskRolePolicy | Out-File -FilePath "apprunner-task-role-trust.json" -Encoding utf8

# GCS アクセス用のIAMポリシー（必要に応じて）
$gcsAccessPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:$Region:*:secret:operation-analysis/gcs-credentials*"
    }
  ]
}
"@

try {
    # Service Role作成
    aws iam create-role --role-name AppRunnerServiceRole --assume-role-policy-document file://apprunner-service-role-trust.json --profile $AWSProfile | Out-Null
    aws iam attach-role-policy --role-name AppRunnerServiceRole --policy-arn arn:aws:iam::aws:policy/service-role/AppRunnerServicePolicyForECRAccess --profile $AWSProfile | Out-Null
    Write-Host "✅ App Runner Service Role を作成しました" -ForegroundColor Green
} catch {
    Write-Host "⚠️ App Runner Service Role は既に存在します" -ForegroundColor Yellow
}

try {
    # Task Role作成
    aws iam create-role --role-name AppRunnerTaskRole --assume-role-policy-document file://apprunner-task-role-trust.json --profile $AWSProfile | Out-Null
    $gcsAccessPolicy | Out-File -FilePath "gcs-access-policy.json" -Encoding utf8
    aws iam put-role-policy --role-name AppRunnerTaskRole --policy-name GCSAccessPolicy --policy-document file://gcs-access-policy.json --profile $AWSProfile | Out-Null
    Write-Host "✅ App Runner Task Role を作成しました" -ForegroundColor Green
} catch {
    Write-Host "⚠️ App Runner Task Role は既に存在します" -ForegroundColor Yellow
}

# AWS Secrets Manager にGCS認証情報を保存（オプション）
Write-Host "🔑 GCS認証情報をSecrets Managerに保存しますか？" -ForegroundColor Yellow
$saveCredentials = Read-Host "GCS認証ファイルのパスを入力してください（スキップする場合はEnter）"

if ($saveCredentials -and (Test-Path $saveCredentials)) {
    try {
        $credentialsContent = Get-Content $saveCredentials -Raw
        aws secretsmanager create-secret --name "operation-analysis/gcs-credentials" --secret-string $credentialsContent --region $Region --profile $AWSProfile | Out-Null
        Write-Host "✅ GCS認証情報をSecrets Managerに保存しました" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ GCS認証情報の保存でエラーが発生しました" -ForegroundColor Yellow
    }
}

# 一時ファイルクリーンアップ
Remove-Item "apprunner-service-role-trust.json" -Force -ErrorAction SilentlyContinue
Remove-Item "apprunner-task-role-trust.json" -Force -ErrorAction SilentlyContinue
Remove-Item "gcs-access-policy.json" -Force -ErrorAction SilentlyContinue

Write-Host "🎉 AWS App Runner セットアップが完了しました！" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "1. GitHubリポジトリにAWSクレデンシャルを設定してください:" -ForegroundColor White
Write-Host "   - AWS_ACCESS_KEY_ID" -ForegroundColor Gray
Write-Host "   - AWS_SECRET_ACCESS_KEY" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "2. コードをプッシュしてGitHub Actionsを実行してください:" -ForegroundColor White
Write-Host "   git push origin main" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
Write-Host "📝 ECRリポジトリURI: $ecrUri" -ForegroundColor Cyan
