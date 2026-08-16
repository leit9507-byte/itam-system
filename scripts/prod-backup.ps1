param(
  [string]$ProjectName = "itam-prod",
  [string]$OutputDir = "backups"
)

$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -lt 7) {
  Write-Error "This script requires PowerShell 7+ (Windows PowerShell 5.1 corrupts binary backups). Install pwsh from https://github.com/PowerShell/PowerShell"
  exit 1
}
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env.production"
if (!(Test-Path $EnvFile)) {
  throw ".env.production not found"
}

$BackupRoot = Join-Path $Root $OutputDir
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Target = Join-Path $BackupRoot $Stamp
New-Item -ItemType Directory -Force -Path $Target | Out-Null

Push-Location $Root
try {
  docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production exec -T mysql sh -c 'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" --single-transaction --routines --triggers --events "$MYSQL_DATABASE"' | Set-Content -Encoding UTF8 (Join-Path $Target "database.sql")
  docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production exec -T backend sh -c 'cd /app/uploads && tar -czf - .' > (Join-Path $Target "uploads.tar.gz")
  @{
    created_at = (Get-Date).ToString("s")
    compose = "docker-compose.prod.yml"
    database = "database.sql"
    uploads = "uploads.tar.gz"
  } | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Target "manifest.json")
  Write-Host "Production backup completed: $Target"
}
finally {
  Pop-Location
}
