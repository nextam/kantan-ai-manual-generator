# GitHub連携によるAWS App Runnerデプロイスクリプト
param(
    [Parameter(Mandatory=$false)]
    [string]$AWSProfile = "default",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "ap-northeast-1",
    
    [Parameter(Mandatory=$false)]
    [string]$AppName = "operation-analysis-app",
    
    [Parameter(Mandatory=$false)]
    [string]$GitHubRepo = "CareerSurvival/kantan-ai-manual-generator",
    
    [Parameter(Mandatory=$false)]
    [string]$Branch = "suzuki"
)

Write-Host "🚀 GitHub連携でAWS App Runnerデプロイを開始します" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor White

# AWS認証確認
Write-Host "📋 AWS認証確認中..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --profile $AWSProfile | ConvertFrom-Json
    Write-Host "✅ AWS認証確認: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS認証に失敗しました" -ForegroundColor Red
    exit 1
}

# App RunnerのGitHub接続設定
Write-Host "🔗 GitHub接続を作成中..." -ForegroundColor Yellow

# GitHub接続作成（初回のみ）
$connectionName = "github-connection-operation-analysis"
try {
    # 既存接続確認
    $existingConnection = aws apprunner list-connections --query "ConnectionSummaryList[?ConnectionName=='$connectionName'].ConnectionArn" --output text --profile $AWSProfile
    
    if ($existingConnection) {
        Write-Host "✅ 既存のGitHub接続を使用: $existingConnection" -ForegroundColor Green
        $connectionArn = $existingConnection
    } else {
        # 新しいGitHub接続作成
        $connectionResult = aws apprunner create-connection --connection-name $connectionName --provider-type GITHUB --profile $AWSProfile | ConvertFrom-Json
        $connectionArn = $connectionResult.Connection.ConnectionArn
        Write-Host "📝 GitHub接続作成中: $connectionArn" -ForegroundColor Cyan
        Write-Host "⚠️  GitHub認証が必要です。AWS Management ConsoleのApp Runner画面で認証を完了してください。" -ForegroundColor Yellow
        
        # 接続状態を確認
        do {
            Start-Sleep 10
            $connectionStatus = aws apprunner describe-connection --connection-arn $connectionArn --query 'Connection.Status' --output text --profile $AWSProfile
            Write-Host "   接続状態: $connectionStatus" -ForegroundColor Gray
            
            if ($connectionStatus -eq "AVAILABLE") {
                Write-Host "✅ GitHub接続が完了しました！" -ForegroundColor Green
                break
            } elseif ($connectionStatus -eq "ERROR") {
                Write-Host "❌ GitHub接続に失敗しました" -ForegroundColor Red
                exit 1
            }
        } while ($connectionStatus -eq "PENDING_HANDSHAKE")
    }
} catch {
    Write-Host "❌ GitHub接続作成エラー: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# App Runnerサービス設定
Write-Host "🔧 App Runnerサービスを設定中..." -ForegroundColor Yellow

$serviceConfig = @{
    ServiceName = $AppName
    SourceConfiguration = @{
        GitHubRepository = @{
            RepositoryUrl = "https://github.com/$GitHubRepo"
            SourceCodeVersion = @{
                Type = "BRANCH"
                Value = $Branch
            }
            CodeConfiguration = @{
                ConfigurationSource = "REPOSITORY"  # apprunner.yamlファイルを使用
            }
            SourceDirectory = "operation_analysis"  # ルートディレクトリ配下のoperation_analysisフォルダ
        }
        ConnectionArn = $connectionArn
        AutoDeploymentsEnabled = $true
    }
    InstanceConfiguration = @{
        Cpu = "1 vCPU"
        Memory = "2 GB"
    }
    HealthCheckConfiguration = @{
        Protocol = "HTTP"
        Path = "/health"
        Interval = 10
        Timeout = 5
        HealthyThreshold = 1
        UnhealthyThreshold = 5
    }
}

# 既存サービス確認
Write-Host "🔍 既存サービスを確認中..." -ForegroundColor Yellow
$existingService = aws apprunner list-services --profile $AWSProfile --query "ServiceSummaryList[?ServiceName=='$AppName'].ServiceArn" --output text

if ($existingService) {
    Write-Host "⚠️  既存のApp Runnerサービスが見つかりました: $AppName" -ForegroundColor Yellow
    $updateService = Read-Host "既存サービスを更新しますか？ (y/N)"
    
    if ($updateService -eq "y" -or $updateService -eq "Y") {
        Write-Host "🔄 既存サービスを更新中..." -ForegroundColor Cyan
        aws apprunner start-deployment --service-arn $existingService --profile $AWSProfile
        $serviceArn = $existingService
    } else {
        Write-Host "❌ デプロイをキャンセルしました" -ForegroundColor Red
        exit 1
    }
} else {
    # 新しいサービス作成
    Write-Host "🆕 新しいApp Runnerサービスを作成中..." -ForegroundColor Cyan
    
    $configJson = $serviceConfig | ConvertTo-Json -Depth 10
    $configJson | Out-File -FilePath "apprunner-github-config.json" -Encoding utf8
    
    try {
        $createResult = aws apprunner create-service --cli-input-json file://apprunner-github-config.json --profile $AWSProfile | ConvertFrom-Json
        $serviceArn = $createResult.Service.ServiceArn
        Write-Host "✅ App Runnerサービス作成開始: $serviceArn" -ForegroundColor Green
    } catch {
        Write-Host "❌ サービス作成失敗: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    } finally {
        # 一時ファイル削除
        Remove-Item "apprunner-github-config.json" -Force -ErrorAction SilentlyContinue
    }
}

# デプロイ完了待機
Write-Host "⏱️  デプロイメント完了を待機中..." -ForegroundColor Yellow
aws apprunner wait service-up --service-arn $serviceArn --profile $AWSProfile

# 結果表示
Write-Host ""
Write-Host "🎉 デプロイメントが完了しました！" -ForegroundColor Green
Write-Host "================================" -ForegroundColor White

$serviceUrl = aws apprunner describe-service --service-arn $serviceArn --profile $AWSProfile --query 'Service.ServiceUrl' --output text
Write-Host "🌐 App Runner Service URL: https://$serviceUrl" -ForegroundColor Cyan
Write-Host "🏥 Health Check: https://$serviceUrl/health" -ForegroundColor Cyan
Write-Host "📱 Operation Analysis: https://$serviceUrl/operation_analysis" -ForegroundColor Cyan

Write-Host ""
Write-Host "📋 サービス情報:" -ForegroundColor Yellow
Write-Host "   Service ARN: $serviceArn" -ForegroundColor Gray
Write-Host "   GitHub Repository: $GitHubRepo" -ForegroundColor Gray
Write-Host "   Branch: $Branch" -ForegroundColor Gray
Write-Host "   Auto Deploy: Enabled" -ForegroundColor Gray

# ブラウザで開く確認
$openBrowser = Read-Host "ブラウザでアプリケーションを開きますか？ (y/N)"
if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
    Start-Process "https://$serviceUrl"
}
