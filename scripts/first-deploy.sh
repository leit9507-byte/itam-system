#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="itam"
RESET_DATA="${1:-}"

cd "$PROJECT_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker was not found. Install Docker first, then run this script again." >&2
  exit 1
fi

docker compose version >/dev/null

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Please review secrets before public deployment."
fi

if [[ "$RESET_DATA" == "--reset-data" ]]; then
  docker compose -p "$PROJECT_NAME" down -v
else
  docker compose -p "$PROJECT_NAME" down
fi

docker compose -p "$PROJECT_NAME" up --build -d
docker compose -p "$PROJECT_NAME" ps

echo
echo "ITAM first deployment is ready."
echo "Frontend: http://127.0.0.1:5173"
echo "Backend:  http://127.0.0.1:8000"
echo "Docs:     http://127.0.0.1:8000/docs"
echo "Default admin: admin / admin"
