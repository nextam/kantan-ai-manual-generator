param(
  [Parameter(Mandatory=$true)] [string]$VpcId,
  [Parameter(Mandatory=$true)] [string[]]$SubnetIds,            # 複数AZ e.g. @('subnet-a','subnet-b') または 'subnet-a,subnet-b'
  [Parameter(Mandatory=$true)] [string]$AlbSgId,
  [Parameter(Mandatory=$true)] [string]$InstanceId,
  [Parameter(Mandatory=$true)] [string]$AcmArn,                 # 提示のARN
  [Parameter(Mandatory=$true)] [string]$HostedZoneId,           # Route53のホストゾーンID
  [Parameter(Mandatory=$true)] [string]$DomainManual,           # manual-generator.kantan-ai.net
  [Parameter(Mandatory=$true)] [string]$DomainAnalysis          # operation-analysis.kantan-ai.net
)

$ErrorActionPreference = 'Stop'

function JQ { param($json,$query) return ($json | ConvertFrom-Json | ForEach-Object { $_.$query }) }

function Get-TargetGroupArn {
  param([string]$name)
  try {
    $resp = aws elbv2 describe-target-groups --names $name | ConvertFrom-Json
    return $resp.TargetGroups[0].TargetGroupArn
  } catch { return $null }
}

function Get-OrCreateTargetGroup {
  param([string]$name,[int]$port,[string]$vpcId,[string]$hcPath)
  $arn = Get-TargetGroupArn -name $name
  if ($arn) { return $arn }
  $tg = aws elbv2 create-target-group --name $name --protocol HTTP --port $port --vpc-id $vpcId --target-type instance --health-check-path $hcPath | ConvertFrom-Json
  return $tg.TargetGroups[0].TargetGroupArn
}

function Get-OrCreateAlb {
  param([string]$name,[string]$sgId,[string[]]$subnets)
  try {
    $resp = aws elbv2 describe-load-balancers --names $name | ConvertFrom-Json
    $lb = $resp.LoadBalancers[0]
  } catch {
    $resp = aws elbv2 create-load-balancer --name $name --type application --scheme internet-facing --security-groups $sgId --subnets @($subnets) | ConvertFrom-Json
    $lb = $resp.LoadBalancers[0]
  }
  return $lb
}

function Get-OrCreateListener {
  param([string]$albArn,[string]$protocol,[int]$port,[string]$certificateArn)
  $ls = aws elbv2 describe-listeners --load-balancer-arn $albArn | ConvertFrom-Json
  $existing = $ls.Listeners | Where-Object { $_.Port -eq $port -and $_.Protocol -eq $protocol }
  if ($existing) { return $existing[0].ListenerArn }
  if ($protocol -eq 'HTTPS') {
    $l = aws elbv2 create-listener --load-balancer-arn $albArn --protocol HTTPS --port 443 --certificates CertificateArn=$certificateArn --default-actions Type=fixed-response,FixedResponseConfig='{StatusCode=404,ContentType=text/plain,MessageBody=Not Found}' | ConvertFrom-Json
  } else {
    $l = aws elbv2 create-listener --load-balancer-arn $albArn --protocol HTTP --port 80 --default-actions Type=redirect,RedirectConfig='Protocol=HTTPS,Port=443,StatusCode=HTTP_301' | ConvertFrom-Json
  }
  return $l.Listeners[0].ListenerArn
}

function Set-HostRule {
  param([string]$listenerArn,[string]$hostName,[string]$targetGroupArn,[int]$basePriority)
  $rules = aws elbv2 describe-rules --listener-arn $listenerArn | ConvertFrom-Json
  $match = $null
  foreach ($r in $rules.Rules) {
    foreach ($c in $r.Conditions) {
      if ($c.Field -eq 'host-header' -and $c.Values -contains $hostName) { $match = $r; break }
    }
    if ($match) { break }
  }
  if ($match) {
    # update action if needed
    $currentTg = $match.Actions[0].TargetGroupArn
    if ($currentTg -ne $targetGroupArn) {
      aws elbv2 modify-rule --rule-arn $match.RuleArn --actions Type=forward,TargetGroupArn=$targetGroupArn | Out-Null
    }
    return $match.RuleArn
  }
  # choose free priority
  $used = @($rules.Rules | Where-Object { $_.Priority -ne 'default' } | ForEach-Object { [int]$_.Priority })
  $priority = $basePriority
  while ($used -contains $priority) { $priority++ }
  aws elbv2 create-rule --listener-arn $listenerArn --priority $priority --conditions Field=host-header,Values=$hostName --actions Type=forward,TargetGroupArn=$targetGroupArn | Out-Null
}

# Normalize SubnetIds: support comma or space separated single string as well
if ($SubnetIds.Count -eq 1 -and $SubnetIds[0] -match ',') {
  $SubnetIds = @($SubnetIds[0].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}
$SubnetIds = @($SubnetIds | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($SubnetIds.Count -lt 2) {
  throw "At least two SubnetIds are required. Got: $($SubnetIds -join ', ')"
}
Write-Host "Using Subnets: $($SubnetIds -join ', ')" -ForegroundColor Yellow

Write-Host "[1/7] ターゲットグループ作成/取得" -ForegroundColor Cyan
try {
  $tgArn1 = Get-OrCreateTargetGroup -name 'tg-manual' -port 8080 -vpcId $VpcId -hcPath '/'
  Write-Host "tg-manual ARN: $tgArn1" -ForegroundColor Yellow
} catch {
  Write-Host "Error creating tg-manual: $_" -ForegroundColor Red
  throw
}
try {
  $tgArn2 = Get-OrCreateTargetGroup -name 'tg-analysis' -port 8081 -vpcId $VpcId -hcPath '/health'
  Write-Host "tg-analysis ARN: $tgArn2" -ForegroundColor Yellow
} catch {
  Write-Host "Error creating tg-analysis: $_" -ForegroundColor Red
  throw
}

Write-Host "[2/7] ターゲット登録" -ForegroundColor Cyan
aws elbv2 register-targets --target-group-arn $tgArn1 --targets Id=$InstanceId,Port=8080 | Out-Null
aws elbv2 register-targets --target-group-arn $tgArn2 --targets Id=$InstanceId,Port=8081 | Out-Null

Write-Host "[3/7] ALB 作成/取得" -ForegroundColor Cyan
$lb = Get-OrCreateAlb -name 'chuden-alb' -sgId $AlbSgId -subnets $SubnetIds
$albArn = $lb.LoadBalancerArn
$albDns = $lb.DNSName
$albHz  = $lb.CanonicalHostedZoneId

Write-Host "[4/7] HTTPS リスナー作成/取得" -ForegroundColor Cyan
$listener443Arn = Get-OrCreateListener -albArn $albArn -protocol 'HTTPS' -port 443 -certificateArn $AcmArn

Write-Host "[5/7] Host ベースルール作成/更新" -ForegroundColor Cyan
Set-HostRule -listenerArn $listener443Arn -hostName $DomainManual -targetGroupArn $tgArn1 -basePriority 10 | Out-Null
Set-HostRule -listenerArn $listener443Arn -hostName $DomainAnalysis -targetGroupArn $tgArn2 -basePriority 20 | Out-Null

Write-Host "[6/7] HTTP→HTTPS リスナー作成/取得" -ForegroundColor Cyan
Get-OrCreateListener -albArn $albArn -protocol 'HTTP' -port 80 -certificateArn '' | Out-Null

Write-Host "[7/7] Route53 レコード作成" -ForegroundColor Cyan
$changeBatch = @{
  Comment = 'ALB alias for subdomains';
  Changes = @(
    @{ Action='UPSERT'; ResourceRecordSet=@{ Name=$DomainManual; Type='A'; AliasTarget=@{ HostedZoneId=$albHz; DNSName=$albDns; EvaluateTargetHealth=$false } } },
    @{ Action='UPSERT'; ResourceRecordSet=@{ Name=$DomainAnalysis; Type='A'; AliasTarget=@{ HostedZoneId=$albHz; DNSName=$albDns; EvaluateTargetHealth=$false } } }
  )
} | ConvertTo-Json -Depth 6

$temp = New-TemporaryFile
[System.IO.File]::WriteAllText($temp.FullName, $changeBatch, [System.Text.UTF8Encoding]::new($false))
try {
  aws route53 change-resource-record-sets --hosted-zone-id $HostedZoneId --change-batch file://$temp | Out-Null
  Write-Host "Route53レコード作成完了" -ForegroundColor Green
} catch {
  Write-Host "Route53エラー: $_" -ForegroundColor Red
  Write-Host "Change batch content:" -ForegroundColor Yellow
  Get-Content $temp
} finally {
  Remove-Item $temp -Force
}

Write-Host "完了: $DomainManual / $DomainAnalysis → $albDns" -ForegroundColor Green
