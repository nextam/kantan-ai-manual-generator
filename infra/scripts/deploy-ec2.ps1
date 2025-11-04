param(
    [Parameter(Mandatory = $true)] [string]$HostName,            # EC2 パブリックIP or DNS
    [Parameter(Mandatory = $true)] [string]$User,                # 例: ec2-user
    [Parameter(Mandatory = $true)] [string]$KeyPath,             # 例: C:\keys\chuden-demoapp.pem
    [string]$RemotePath = "/opt/chuden-demoapp"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-SSH {
    param([string]$Command)
    ssh -i $KeyPath "$User@$HostName" $Command
}

function Copy-ToRemote {
    param([string]$Source, [string]$Dest)
    $target = "${User}@${HostName}:$Dest"
    scp -i $KeyPath -r $Source $target
}

Write-Host "[1/5] EC2 へ初期セットアップ (Docker/Docker Compose)" -ForegroundColor Cyan
Invoke-SSH "sudo yum -y update || sudo apt-get -y update"
Invoke-SSH "(command -v docker >/dev/null 2>&1) || curl -fsSL https://get.docker.com | sh"
Invoke-SSH "sudo usermod -aG docker $User && sudo systemctl enable --now docker"
Invoke-SSH "if ! command -v docker-compose >/dev/null 2>&1; then sudo curl -L 'https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-\$(uname -s)-\$(uname -m)' -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose; fi"

Write-Host "[2/5] リモート配置先ディレクトリ作成: $RemotePath" -ForegroundColor Cyan
Invoke-SSH "sudo mkdir -p $RemotePath $RemotePath/manual_generator/instance $RemotePath/manual_generator/logs $RemotePath/manual_generator/uploads && sudo chown -R ${User}:${User} $RemotePath"

Write-Host "[3/5] 必要ファイルのみ同期" -ForegroundColor Cyan
# 重要: 秘密鍵(.pem)や .git は送らない
Copy-ToRemote "./docker-compose.yml" "$RemotePath/"
Copy-ToRemote "./manual_generator" "$RemotePath/"
Copy-ToRemote "./operation_analysis" "$RemotePath/"
Copy-ToRemote "./infra" "$RemotePath/"

Write-Host "[4/5] docker compose 起動" -ForegroundColor Cyan
Invoke-SSH "bash -lc 'cd $RemotePath && (command -v docker-compose >/dev/null 2>&1 || sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose || true)'"
Invoke-SSH "bash -lc 'cd $RemotePath && sudo docker-compose pull || true'"
Invoke-SSH "bash -lc 'cd $RemotePath && sudo docker-compose build'"
Invoke-SSH "bash -lc 'cd $RemotePath && sudo docker-compose up -d'"

Write-Host "[5/5] ヘルスチェック" -ForegroundColor Cyan
Invoke-SSH "bash -lc 'curl -s http://127.0.0.1:8080/health || true'"
Invoke-SSH "bash -lc 'curl -s http://127.0.0.1:8081/health || true'"

# 既存の SQLite を named volume へ一度だけ移行（存在すれば）
$dbPath = "$RemotePath/manual_generator/instance/manual_generator.db"
Write-Host "[Migration] 旧DBの存在確認と移行: $dbPath" -ForegroundColor Cyan
Invoke-SSH "bash -lc 'if [ -f "$dbPath" ]; then echo "Found existing DB at $dbPath. Copying into container volume..."; docker cp "$dbPath" manual-generator:/app/instance/; echo "Done."; else echo "No legacy DB found at $dbPath"; fi'"

Write-Host "デプロイ完了:" -ForegroundColor Green
Write-Host ("  manual:   http://{0}:8080/" -f $HostName)
Write-Host ("  analysis: http://{0}:8081/" -f $HostName)
