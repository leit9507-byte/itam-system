param(
  [Parameter(Mandatory = $true)][string]$BackupPath,
  [string]$ProjectName = "itam-prod",
  [switch]$RestoreUploads
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ResolvedBackup = Resolve-Path $BackupPath
$DbFile = Join-Path $ResolvedBackup "database.sql"
$UploadsFile = Join-Path $ResolvedBackup "uploads.tar.gz"

if (!(Test-Path (Join-Path $Root ".env.production"))) {
  throw ".env.production not found"
}
if (!(Test-Path $DbFile)) {
  throw "database.sql not found in $ResolvedBackup"
}

Push-Location $Root
try {
  Write-Host "Restoring database from $DbFile"
  Get-Content $DbFile -Raw | docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production exec -T mysql sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"'

  if ($RestoreUploads) {
    if (!(Test-Path $UploadsFile)) {
      throw "uploads.tar.gz not found in $ResolvedBackup"
    }
    Write-Host "Restoring uploads from $UploadsFile"
    Get-Content $UploadsFile -Raw | docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production exec -T backend sh -c 'mkdir -p /app/uploads && cd /app/uploads && tar -xzf -'
  }

  Write-Host "Restore completed from: $ResolvedBackup"
}
finally {
  Pop-Location
}
