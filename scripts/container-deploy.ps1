param(
  [switch]$Rebuild,
  [switch]$ResetData
)

$ErrorActionPreference = "Stop"
$ProjectName = "itam"

if ($ResetData) {
  docker compose -p $ProjectName down -v
} else {
  docker compose -p $ProjectName down
}

if ($Rebuild) {
  docker compose -p $ProjectName up --build -d
} else {
  docker compose -p $ProjectName up -d
}

docker compose -p $ProjectName ps

Write-Host ""
Write-Host "ITAM container deployment is ready."
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Docs:     http://127.0.0.1:8000/docs"
