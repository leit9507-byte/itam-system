param(
  [switch]$ResetData
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ProjectName = "itam"

Set-Location $ProjectRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker was not found. Install Docker Desktop first, then run this script again."
}

docker compose version | Out-Null

if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Please review secrets before public deployment."
}

if ($ResetData) {
  docker compose -p $ProjectName down -v
} else {
  docker compose -p $ProjectName down
}

docker compose -p $ProjectName up --build -d
docker compose -p $ProjectName ps

Write-Host ""
Write-Host "ITAM first deployment is ready."
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Docs:     http://127.0.0.1:8000/docs"
Write-Host "Default admin: admin，密码来自 .env 的 INITIAL_ADMIN_PASSWORD（默认 Admin@123456，首次登录后请立即修改）"
