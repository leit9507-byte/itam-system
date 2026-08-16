param(
  [Parameter(Mandatory = $true)][string]$BackupPath,
  [string]$ProjectName = "itam-prod",
  [switch]$RestoreUploads
)

$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -lt 7) {
  Write-Error "This script requires PowerShell 7+ (Windows PowerShell 5.1 corrupts binary backups). Install pwsh from https://github.com/PowerShell/PowerShell"
  exit 1
}
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
    # uploads.tar.gz is a binary tar archive; PowerShell pipes are not binary-safe.
    # Extract the archive on the host and copy it into the container with docker cp, e.g.:
    #   tar -xzf "$UploadsFile" -C "$env:TEMP/itam-uploads"
    #   docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production exec -T backend sh -c 'mkdir -p /app/uploads'
    #   docker cp "$env:TEMP/itam-uploads/." itam-prod-backend:/app/uploads/
    Write-Host "Skipping automatic uploads restore. Please extract $UploadsFile manually and use docker cp (see instructions in $($MyInvocation.MyCommand.Path))."
  }

  Write-Host "Restore completed from: $ResolvedBackup"
}
finally {
  Pop-Location
}
