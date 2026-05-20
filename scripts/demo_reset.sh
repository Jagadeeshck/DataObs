#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"

echo "[demo_reset] Stopping POC stack and removing volumes..."
docker compose -f docker-compose.poc.yml --env-file .env.poc down -v --remove-orphans
