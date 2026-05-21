#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"
RUN_MODE="${1:-good}"
SCALE="${2:-small}"
MODE="${3:-fixture}"
export DATAOBS_POC_SINK=elasticsearch
if [[ "$MODE" == "live" ]]; then
  export DATAOBS_POC_FIXTURE_MODE=false
else
  export DATAOBS_POC_FIXTURE_MODE="${DATAOBS_POC_FIXTURE_MODE:-true}"
fi
export DATAOBS_DEMO_SCENARIO=road_safety
export DATAOBS_DEMO_RUN_MODE="$RUN_MODE"
export DATAOBS_DEMO_SCALE="$SCALE"
DEMO_REBUILD="${DEMO_REBUILD:-true}"
echo "[demo_run] scenario=$DATAOBS_DEMO_SCENARIO run_mode=$RUN_MODE scale=$SCALE mode=$MODE fixture_mode=$DATAOBS_POC_FIXTURE_MODE"
if [[ "$DEMO_REBUILD" == "true" ]]; then
  echo "[demo_run] Rebuilding pipeline image to avoid stale demo code (set DEMO_REBUILD=false to skip)."
  docker compose -f docker-compose.poc.yml --env-file .env.poc build pipeline
else
  echo "[demo_run] WARNING: DEMO_REBUILD=false. If code changed, rebuild first: docker compose -f docker-compose.poc.yml --env-file .env.poc build pipeline"
fi
docker compose -f docker-compose.poc.yml --env-file .env.poc run --rm pipeline
cat <<EOF

Next checks:
- Dashboards: DataObs Road Safety Executive Overview; Data Quality & Bad Data Detection; Freshness / Volume / Schema Drift; Lineage & Impact; Spark Pipeline Performance
- Indices: dataobs-rs-* , dataobs-quality, dataobs-alerts, dataobs-freshness, dataobs-volume, dataobs-schema, dataobs-lineage, dataobs-spark-metrics
- Run bad demo after good: ./scripts/demo_run.sh bad ${SCALE}
EOF
