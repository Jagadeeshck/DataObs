#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"

echo "[demo_run] Running pipeline with Elasticsearch sink (fail-fast)."
export DATAOBS_POC_SINK=elasticsearch
export DATAOBS_POC_FIXTURE_MODE="${DATAOBS_POC_FIXTURE_MODE:-true}"

docker compose -f docker-compose.poc.yml --env-file .env.poc run --rm pipeline

echo
echo "Next: ./scripts/demo_verify.sh"
