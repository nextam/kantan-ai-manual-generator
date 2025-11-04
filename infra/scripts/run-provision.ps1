param(
  [Parameter(Mandatory=$true)] [string]$InstanceId,
  [Parameter(Mandatory=$true)] [string]$AcmArn,
  [Parameter(Mandatory=$true)] [string]$RootDomain,              # kantan-ai.net
  [string]$Region = 'ap-northeast-1',
  [string]$AlbSgName = 'chuden-alb-sg',
  [string]$DomainManual = "manual.$RootDomain",
  [string]$DomainAnalysis = "analysis.$RootDomain",
  [string[]]$SubnetIds                      # 明示指定: 2つ以上のPublic Subnetを渡すと自動検出をスキップ
)

$ErrorActionPreference = 'Stop'

function Write-Utf8NoBom([string]$Path,[string]$Text) {
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

function Get-HostedZoneId([string]$root) {
  $hz = aws route53 list-hosted-zones-by-name --dns-name $root | ConvertFrom-Json
  $zone = $hz.HostedZones | Where-Object { $_.Name.TrimEnd('.') -eq $root }
  if (-not $zone) { throw "Hosted zone not found for $root" }
  return ($zone.Id -replace '^/hostedzone/', '')
}

function Set-AlbSecurityGroup([string]$vpcId,[string]$name) {
  $sg = aws ec2 describe-security-groups --filters Name=vpc-id,Values=$vpcId Name=group-name,Values=$name | ConvertFrom-Json
  if ($sg.SecurityGroups.Count -eq 0) {
    Write-Host "Creating ALB SG $name" -ForegroundColor Yellow
    $sg = aws ec2 create-security-group --vpc-id $vpcId --group-name $name --description "ALB SG for $name" | ConvertFrom-Json
    $sgId = $sg.GroupId
  } else { $sgId = $sg.SecurityGroups[0].GroupId }
  # allow 80/443 from 0.0.0.0/0
  foreach ($p in 80,443) {
  try { aws ec2 authorize-security-group-ingress --group-id $sgId --protocol tcp --port $p --cidr 0.0.0.0/0 2>$null | Out-Null } catch { }
  }
  return $sgId
}

## Note: Instance SG ingress for 8080/8081 from ALB SG is assumed to exist.

Write-Host "[0] Resolving context from AWS..." -ForegroundColor Cyan
$env:AWS_DEFAULT_REGION = $Region
$inst = aws ec2 describe-instances --instance-ids $InstanceId | ConvertFrom-Json
$vpcId = $inst.Reservations[0].Instances[0].VpcId
# Instance subnet not needed here; using public subnets detection below

if (-not $SubnetIds -or $SubnetIds.Count -eq 0) {
  # Public Subnet 検出: IGW への 0.0.0.0/0 ルートを持つ RouteTable に関連付く Subnet を採用
  $allSubnets = aws ec2 describe-subnets --filters Name=vpc-id,Values=$vpcId | ConvertFrom-Json
  $rtbs = aws ec2 describe-route-tables --filters Name=vpc-id,Values=$vpcId | ConvertFrom-Json
  $publicSubnetSet = New-Object System.Collections.Generic.HashSet[string]
  foreach ($rt in $rtbs.RouteTables) {
    $hasIgwDefault = $false
    foreach ($r in $rt.Routes) { if ($r.DestinationCidrBlock -eq '0.0.0.0/0' -and $r.GatewayId -like 'igw-*') { $hasIgwDefault = $true; break } }
    if (-not $hasIgwDefault) { continue }
    foreach ($assoc in $rt.Associations) {
      if ($assoc.SubnetId) { [void]$publicSubnetSet.Add($assoc.SubnetId) }
    }
  }
  $publicSubs = @()
  foreach ($s in $allSubnets.Subnets) { if ($publicSubnetSet.Contains($s.SubnetId)) { $publicSubs += $s } }
  if ($publicSubs.Count -lt 2) {
    throw "Need at least 2 public subnets in VPC $vpcId. Provide -SubnetIds explicitly or add another public subnet."
  }
  $byAz = $publicSubs | Group-Object AvailabilityZone
  $chosen = @()
  foreach ($g in $byAz) { $chosen += $g.Group[0] }
  $chosen = $chosen | Select-Object -First 2
  $SubnetIds = @($chosen | ForEach-Object { $_.SubnetId })
}

Write-Host ("Using VPC {0}, Subnets: {1}" -f $vpcId, ($SubnetIds -join ', ')) -ForegroundColor Yellow

$albSgId = Set-AlbSecurityGroup -vpcId $vpcId -name $AlbSgName
Write-Host "ALB SG: $albSgId" -ForegroundColor Yellow

$hostedZoneId = Get-HostedZoneId -root $RootDomain
Write-Host "HostedZoneId: $hostedZoneId" -ForegroundColor Yellow

# Call provision script
$scriptPath = Join-Path $PSScriptRoot 'provision-alb-route53.ps1'
& $scriptPath -VpcId $vpcId -SubnetIds $SubnetIds -AlbSgId $albSgId -InstanceId $InstanceId -AcmArn $AcmArn -HostedZoneId $hostedZoneId -DomainManual $DomainManual -DomainAnalysis $DomainAnalysis

Write-Host "Done." -ForegroundColor Green
