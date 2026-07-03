param(
  [string]$ComposeFile = "docker-compose.yml",
  [string]$ProjectName = "itam",
  [string]$Database = "itam_system",
  [string]$DbUser = "itam",
  [string]$DbPassword = "itam_pass",
  [string]$OutputDir = "backups"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BackupRoot = Join-Path $Root $OutputDir
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Target = Join-Path $BackupRoot $Stamp
$DbFile = Join-Path $Target "database.sql"
$UploadSource = Join-Path $Root "uploads"
$UploadTarget = Join-Path $Target "uploads"

New-Item -ItemType Directory -Force -Path $Target | Out-Null

Push-Location $Root
try {
  docker compose -p $ProjectName -f $ComposeFile exec -T mysql mysqldump -u$DbUser -p$DbPassword $Database | Set-Content -Encoding UTF8 $DbFile
  if (Test-Path $UploadSource) {
    Copy-Item -Path $UploadSource -Destination $UploadTarget -Recurse -Force
  }
  @{
    created_at = (Get-Date).ToString("s")
    database = $DbFile
    uploads = $UploadTarget
  } | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Target "manifest.json")
  Write-Host "Backup completed: $Target"
}
finally {
  Pop-Location
}
