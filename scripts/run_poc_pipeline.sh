#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# DataObs POC — run the full pipeline and bootstrap Kibana dashboards
# ─────────────────────────────────────────────────────────────────────────────
# Prerequisites:
#   1. Elasticsearch + Kibana + OTel Collector running (docker compose up -d)
#   2. Python env with requirements-poc.txt installed
#   3. poc.enabled: true in config/dataobs.yaml
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT"

echo "════════════════════════════════════════════"
echo " DataObs POC Pipeline"
echo "════════════════════════════════════════════"

echo ""
echo "[1/2] Running Spark pipeline..."
python -m src.poc.spark_job

echo ""
echo "[2/2] Bootstrapping Kibana saved objects & data views..."
python -m src.poc.bootstrap_kibana

echo ""
echo "════════════════════════════════════════════"
echo " POC pipeline complete!"
echo " Open Kibana: ${KIBANA_URL:-http://localhost:5601}"
echo " Dashboards:"
echo "   • [DataObs POC] Pipeline Health"
echo "   • [DataObs POC] Data Quality Overview"
echo "   • [DataObs POC] Public Dataset Explorer"
echo "════════════════════════════════════════════"
