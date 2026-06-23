param(
  [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$ProjectName = "itam"
$Files = @("-f", "docker-compose.yml", "-f", "docker-compose.dev.yml")

docker compose -p $ProjectName @Files down

if ($Rebuild) {
  docker compose -p $ProjectName @Files up --build -d
} else {
  docker compose -p $ProjectName @Files up -d
}

docker compose -p $ProjectName @Files ps

Write-Host ""
Write-Host "ITAM container development mode is ready."
Write-Host "Frontend dev server: http://127.0.0.1:5173"
Write-Host "Backend API:          http://127.0.0.1:8000"
