#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="${PROJECT_NAME:-itam-prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
INIT_URL="${INIT_URL:-http://127.0.0.1:8000/ops/init-database}"

cd "$ROOT_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Copy .env.production.example and update secrets first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${INIT_DATABASE_TOKEN:-}" ]]; then
  echo "INIT_DATABASE_TOKEN is required in $ENV_FILE." >&2
  exit 1
fi

echo "Starting MySQL and backend..."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d mysql backend

echo "Running Alembic migrations..."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend alembic upgrade head

echo "Restarting backend so runtime database config is reloaded..."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart backend

echo "Waiting for backend..."
for attempt in {1..30}; do
  if docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "Backend did not become ready in time." >&2
    exit 1
  fi
  sleep 2
done

echo "Seeding base data through ops init endpoint..."
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend python -c "
import json
import os
import urllib.request

url = os.getenv('INIT_URL', '$INIT_URL')
token = os.getenv('INIT_DATABASE_TOKEN')
payload = json.dumps({'force': True}).encode()
request = urllib.request.Request(
    url,
    data=payload,
    headers={'Content-Type': 'application/json', 'X-Init-Token': token},
    method='POST',
)
with urllib.request.urlopen(request, timeout=60) as response:
    print(response.read().decode())
"

echo "Database initialization complete."
