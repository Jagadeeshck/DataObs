#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# DataObs — one-command local MVP stack launcher
#
# Boots Elasticsearch 9.5.5 + migrations + demo-seed + API + Console locally.
# Run this from your own terminal (needs Docker Desktop with socket access).
#
#   ./scripts/run-mvp-local.sh          # start the stack
#   ./scripts/run-mvp-local.sh down     # stop (keeps data)
#   ./scripts/run-mvp-local.sh clean    # stop and wipe the ES volume
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE=".env.mvp"
COMPOSE_FILE="docker-compose.mvp.yml"

# Prefer the compose plugin; fall back to the standalone binary.
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
else
  COMPOSE="docker-compose"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Creating $ENV_FILE from the example — set real values before any shared use."
  cp .env.mvp.example "$ENV_FILE"
fi

case "${1:-up}" in
  up)
    echo "Starting DataObs MVP stack (ES 9.5.5 → migrations → seed → API → Console)…"
    $COMPOSE --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up --build -d
    echo
    echo "Waiting for the API to become healthy…"
    for i in $(seq 1 60); do
      if curl -fsS http://localhost:8080/health >/dev/null 2>&1; then
        echo "✅ API healthy at http://localhost:8080"
        break
      fi
      sleep 5
    done
    echo "✅ Console at  http://localhost:3000"
    echo "✅ API docs at http://localhost:8080/docs"
    echo
    echo "Tail logs with:  $COMPOSE -f $COMPOSE_FILE logs -f"
    ;;
  down)
    $COMPOSE --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
    ;;
  clean)
    $COMPOSE --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v
    ;;
  *)
    echo "Usage: $0 [up|down|clean]"
    exit 1
    ;;
esac
