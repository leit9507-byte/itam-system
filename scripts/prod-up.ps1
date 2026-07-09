param(
  [string]$ProjectName = "itam-prod",
  [switch]$Build
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env.production"

if (!(Test-Path $EnvFile)) {
  throw ".env.production not found. Copy .env.production.example to .env.production and change all passwords/secrets first."
}

Push-Location $Root
try {
  if ($Build) {
    docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production up --build -d
  } else {
    docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production up -d
  }
  docker compose -p $ProjectName -f docker-compose.prod.yml --env-file .env.production ps
}
finally {
  Pop-Location
}
