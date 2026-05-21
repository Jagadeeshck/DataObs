#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"
./scripts/verify_poc.sh
./scripts/validate_kibana_saved_objects.py

ES_HOST="${ES_HOST:-http://localhost:9200}"; ES_USER="${ES_USER:-elastic}"; ES_PASS="${ELASTIC_PASSWORD:-${ES_PASS:-dataobs_poc_elastic}}"
KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"; KIBANA_USER="${KIBANA_USERNAME:-${ES_USER}}"; KIBANA_PASS="${KIBANA_PASSWORD:-${ES_PASS}}"
AUTH=(-u "${ES_USER}:${ES_PASS}")
KAUTH=(-u "${KIBANA_USER}:${KIBANA_PASS}")
for idx in dataobs-rs-accident-facts dataobs-rs-authority-risk-summary dataobs-rs-road-risk-summary dataobs-rs-vehicle-risk-summary dataobs-rs-casualty-severity-summary dataobs-spark-metrics; do
 c=$(curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}/_count"|sed -n 's/.*"count":\([0-9]*\).*/\1/p'); [ "${c:-0}" -gt 0 ] || { echo "❌ ${idx} empty"; exit 1; }; echo "✅ ${idx} count=${c}";
done

expected=(
  "DataObs Road Safety Executive Overview"
  "Data Quality & Bad Data Detection"
  "Freshness / Volume / Schema Drift"
  "Lineage & Impact"
  "Spark Pipeline Performance"
)

dash_json=$(curl -sf "${KAUTH[@]}" -H 'kbn-xsrf: true' "${KIBANA_URL}/api/saved_objects/_find?type=dashboard&per_page=200")
for t in "${expected[@]}"; do
  echo "$dash_json" | grep -Fq "\"title\":\"${t}\"" || { echo "❌ dashboard missing: ${t}"; exit 1; }
  echo "✅ dashboard exists: ${t}"
done
