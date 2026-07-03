param(
  [Parameter(Mandatory = $true)][string]$BackupPath,
  [string]$ComposeFile = "docker-compose.yml",
  [string]$ProjectName = "itam",
  [string]$Database = "itam_system",
  [string]$DbUser = "itam",
  [string]$DbPassword = "itam_pass",
  [switch]$RestoreUploads
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ResolvedBackup = Resolve-Path $BackupPath
$DbFile = Join-Path $ResolvedBackup "database.sql"
$UploadSource = Join-Path $ResolvedBackup "uploads"
$UploadTarget = Join-Path $Root "uploads"

if (!(Test-Path $DbFile)) {
  throw "database.sql not found in $ResolvedBackup"
}

Push-Location $Root
try {
  Get-Content $DbFile -Raw | docker compose -p $ProjectName -f $ComposeFile exec -T mysql mysql -u$DbUser -p$DbPassword $Database
  if ($RestoreUploads -and (Test-Path $UploadSource)) {
    New-Item -ItemType Directory -Force -Path $UploadTarget | Out-Null
    Copy-Item -Path (Join-Path $UploadSource "*") -Destination $UploadTarget -Recurse -Force
  }
  Write-Host "Restore completed from: $ResolvedBackup"
}
finally {
  Pop-Location
}
