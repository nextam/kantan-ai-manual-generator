# AWS CLI インストールガイド（Windows）

## 🎯 概要
Operation AnalysisをAWS App Runnerにデプロイするために、AWS CLIのインストールが必要です。

## 📋 インストール方法

### Method 1: MSIインストーラー（推奨）

#### Step 1: インストーラーダウンロード
1. ブラウザで以下のURLにアクセス：
   ```
   https://awscli.amazonaws.com/AWSCLIV2.msi
   ```
2. または、PowerShellで自動ダウンロード：
   ```powershell
   $url = "https://awscli.amazonaws.com/AWSCLIV2.msi"
   $output = "$env:TEMP\AWSCLIV2.msi"
   Invoke-WebRequest -Uri $url -OutFile $output
   Start-Process -FilePath $output
   ```

#### Step 2: インストール実行
1. ダウンロードしたMSIファイルを実行
2. インストールウィザードの指示に従って進行
3. デフォルト設定で「Next」→「Install」→「Finish」

#### Step 3: インストール確認
1. **新しいPowerShellウィンドウを開く**（重要）
2. バージョン確認：
   ```powershell
   aws --version
   ```
3. 成功例：
   ```
   aws-cli/2.13.25 Python/3.11.5 Windows/10 exe/AMD64 prompt/off
   ```

### Method 2: PowerShellからの直接実行

```powershell
# 1. インストーラーダウンロード&実行
Write-Host "🌐 AWS CLI v2をダウンロード中..." -ForegroundColor Yellow
$url = "https://awscli.amazonaws.com/AWSCLIV2.msi"
$installer = "$env:TEMP\AWSCLIV2.msi"
Invoke-WebRequest -Uri $url -OutFile $installer

Write-Host "📦 インストール実行中..." -ForegroundColor Cyan
Start-Process -FilePath $installer -ArgumentList "/quiet" -Wait

Write-Host "✅ インストール完了！新しいPowerShellを開いて確認してください" -ForegroundColor Green

# 2. 新しいPowerShellセッションで確認
# aws --version
```

### Method 3: Chocolatey使用（上級者向け）

#### Chocolateyインストール（未インストールの場合）：
```powershell
# 管理者権限PowerShellで実行
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### AWS CLI インストール：
```powershell
choco install awscli -y
```

### Method 4: Python pip使用（開発者向け）

```powershell
# Python3が必要
pip install awscli
```

## 🔧 インストール後の設定

### Step 1: AWS認証情報設定
```powershell
aws configure
```

入力項目：
```
AWS Access Key ID [None]: [あなたのアクセスキー]
AWS Secret Access Key [None]: [あなたのシークレットキー] 
Default region name [None]: ap-northeast-1
Default output format [None]: json
```

### Step 2: 接続テスト
```powershell
# ID確認
aws sts get-caller-identity

# 成功例：
# {
#     "UserId": "AIDACKCEVSQ6C2EXAMPLE",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/DevUser"
# }
```

## 🚨 トラブルシューティング

### 問題1: "aws" コマンドが認識されない

**解決方法：**
1. PowerShellを完全に閉じて新しいセッションを開く
2. 環境変数PATHを確認：
   ```powershell
   $env:PATH -split ';' | Select-String 'AWS'
   ```
3. 手動でパス追加（必要な場合）：
   ```powershell
   $env:PATH += ";C:\Program Files\Amazon\AWSCLIV2"
   ```

### 問題2: インストーラーが見つからない

**解決方法：**
1. ブラウザで直接ダウンロード：
   - https://awscli.amazonaws.com/AWSCLIV2.msi
2. ダウンロードフォルダから手動実行

### 問題3: 権限エラー

**解決方法：**
1. PowerShellを「管理者として実行」
2. 実行ポリシー確認：
   ```powershell
   Get-ExecutionPolicy
   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### 問題4: 古いバージョンが残っている

**解決方法：**
1. 既存AWS CLI アンインストール（コントロールパネル）
2. 新しいバージョンを再インストール

## 📋 確認チェックリスト

- [ ] AWS CLI v2インストール完了
- [ ] `aws --version` でバージョン表示確認
- [ ] `aws configure` で認証情報設定完了
- [ ] `aws sts get-caller-identity` で接続テスト成功

## 🎯 次のステップ

AWS CLIインストール完了後：
1. **AWS App Runner環境セットアップ**
   ```powershell
   cd c:\Users\suusa\OneDrive\Documents\GitHub\kantan-ai-manual-generator\infra\scripts
   .\setup-apprunner-fixed.ps1
   ```

2. **Operation Analysis デプロイ**
   ```powershell
   .\deploy-operation-analysis-apprunner.ps1
   ```

## 📚 参考リンク

- [AWS CLI公式インストールガイド](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [AWS CLI設定方法](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)
- [AWS App Runner公式ドキュメント](https://docs.aws.amazon.com/apprunner/)

---

このガイドに従ってAWS CLIをインストールし、Operation AnalysisのAWS App Runnerデプロイの準備を完了してください。
