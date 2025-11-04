# AWS CLI インストール確認と次ステップスクリプト
param(
    [switch]$CheckOnly,
    [switch]$Install,
    [switch]$Configure
)

Write-Host "🚀 AWS CLI セットアップスクリプト" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor White

# AWS CLI インストール状況確認
function Test-AwsCliInstalled {
    try {
        $version = aws --version 2>$null
        if ($version) {
            Write-Host "✅ AWS CLI インストール済み: $version" -ForegroundColor Green
            return $true
        }
    } catch {
        # 何もしない
    }
    
    Write-Host "❌ AWS CLI がインストールされていません" -ForegroundColor Red
    return $false
}

# AWS CLI インストール
function Install-AwsCli {
    Write-Host "📦 AWS CLI v2 インストール開始..." -ForegroundColor Yellow
    
    try {
        # インストーラーダウンロード
        $url = "https://awscli.amazonaws.com/AWSCLIV2.msi"
        $installer = "$env:TEMP\AWSCLIV2.msi"
        
        Write-Host "🌐 インストーラーダウンロード中..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        
        if (Test-Path $installer) {
            Write-Host "✅ ダウンロード完了: $installer" -ForegroundColor Green
            
            # インストール実行
            Write-Host "🔧 インストール実行中（少々お待ちください）..." -ForegroundColor Yellow
            $process = Start-Process -FilePath $installer -ArgumentList "/quiet" -Wait -PassThru
            
            if ($process.ExitCode -eq 0) {
                Write-Host "✅ AWS CLI インストール完了！" -ForegroundColor Green
                Write-Host "⚠️  新しいPowerShellセッションを開いて確認してください" -ForegroundColor Yellow
                return $true
            } else {
                Write-Host "❌ インストール失敗（Exit Code: $($process.ExitCode)）" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "❌ インストーラーダウンロード失敗" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ インストールエラー: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# AWS CLI 設定
function Set-AwsConfiguration {
    Write-Host "🔑 AWS CLI 設定開始..." -ForegroundColor Yellow
    Write-Host "以下の情報を準備してください:" -ForegroundColor Cyan
    Write-Host "- AWS Access Key ID" -ForegroundColor White
    Write-Host "- AWS Secret Access Key" -ForegroundColor White
    Write-Host "- Default region (推奨: ap-northeast-1)" -ForegroundColor White
    Write-Host ""
    
    # 既存設定確認
    try {
        $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
        if ($identity) {
            Write-Host "✅ AWS認証情報が既に設定されています:" -ForegroundColor Green
            Write-Host "   Account: $($identity.Account)" -ForegroundColor Gray
            Write-Host "   User ARN: $($identity.Arn)" -ForegroundColor Gray
            
            $reconfigure = Read-Host "再設定しますか？ (y/N)"
            if ($reconfigure -ne "y" -and $reconfigure -ne "Y") {
                return $true
            }
        }
    } catch {
        # 認証情報未設定
    }
    
    # 設定実行
    Write-Host "📝 AWS認証情報を設定します..." -ForegroundColor Cyan
    aws configure
    
    # 設定確認
    try {
        Write-Host "🔍 設定確認中..." -ForegroundColor Yellow
        $identity = aws sts get-caller-identity | ConvertFrom-Json
        Write-Host "✅ AWS認証設定成功:" -ForegroundColor Green
        Write-Host "   Account: $($identity.Account)" -ForegroundColor Gray
        Write-Host "   User ARN: $($identity.Arn)" -ForegroundColor Gray
        return $true
    } catch {
        Write-Host "❌ AWS認証設定失敗または不正な認証情報" -ForegroundColor Red
        return $false
    }
}

# 次のステップ表示
function Show-NextSteps {
    Write-Host ""
    Write-Host "🎯 次のステップ:" -ForegroundColor Cyan
    Write-Host "1. AWS App Runner環境セットアップ:" -ForegroundColor White
    Write-Host "   .\setup-apprunner-fixed.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Operation Analysis デプロイ:" -ForegroundColor White
    Write-Host "   .\deploy-operation-analysis-apprunner.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. GitHub Actions自動デプロイ設定:" -ForegroundColor White
    Write-Host "   - GitHubリポジトリにAWSクレデンシャル設定" -ForegroundColor Gray
    Write-Host "   - git push origin main でデプロイ実行" -ForegroundColor Gray
    Write-Host ""
}

# メイン処理
$isInstalled = Test-AwsCliInstalled

if ($CheckOnly) {
    if ($isInstalled) {
        Show-NextSteps
    } else {
        Write-Host "AWS CLI をインストールしてください:" -ForegroundColor Yellow
        Write-Host ".\aws-cli-setup.ps1 -Install" -ForegroundColor Gray
    }
    exit 0
}

if ($Install -or -not $isInstalled) {
    if (-not $isInstalled) {
        $installResult = Install-AwsCli
        if (-not $installResult) {
            Write-Host ""
            Write-Host "❌ 自動インストールに失敗しました" -ForegroundColor Red
            Write-Host "手動でインストールしてください:" -ForegroundColor Yellow
            Write-Host "1. https://awscli.amazonaws.com/AWSCLIV2.msi をダウンロード" -ForegroundColor Gray
            Write-Host "2. インストーラーを実行" -ForegroundColor Gray
            Write-Host "3. 新しいPowerShellセッションで .\aws-cli-setup.ps1 -Configure を実行" -ForegroundColor Gray
            exit 1
        }
        
        Write-Host ""
        Write-Host "⚠️  重要: 新しいPowerShellセッションを開いて、以下を実行してください:" -ForegroundColor Yellow
        Write-Host ".\aws-cli-setup.ps1 -Configure" -ForegroundColor White
        exit 0
    }
}

if ($Configure -or $isInstalled) {
    if (-not $isInstalled) {
        Write-Host "❌ AWS CLI がインストールされていません" -ForegroundColor Red
        Write-Host "先に -Install オプションを実行してください" -ForegroundColor Yellow
        exit 1
    }
    
    $configResult = Set-AwsConfiguration
    if ($configResult) {
        Show-NextSteps
    }
}

# デフォルト動作（引数なし）
if (-not $CheckOnly -and -not $Install -and -not $Configure) {
    if ($isInstalled) {
        Write-Host "AWS CLI は既にインストールされています" -ForegroundColor Green
        $configResult = Set-AwsConfiguration
        if ($configResult) {
            Show-NextSteps
        }
    } else {
        Write-Host "AWS CLI インストールを開始します..." -ForegroundColor Yellow
        $installResult = Install-AwsCli
        if ($installResult) {
            Write-Host ""
            Write-Host "⚠️  新しいPowerShellセッションを開いて設定を続行してください:" -ForegroundColor Yellow
            Write-Host ".\aws-cli-setup.ps1 -Configure" -ForegroundColor White
        }
    }
}
