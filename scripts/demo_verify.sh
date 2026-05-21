#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"
./scripts/verify_poc.sh
ES_HOST="${ES_HOST:-http://localhost:9200}"; ES_USER="${ES_USER:-elastic}"; ES_PASS="${ELASTIC_PASSWORD:-${ES_PASS:-dataobs_poc_elastic}}"
AUTH=(-u "${ES_USER}:${ES_PASS}")
for idx in dataobs-rs-accident-facts dataobs-rs-authority-risk-summary dataobs-rs-road-risk-summary dataobs-rs-vehicle-risk-summary dataobs-rs-casualty-severity-summary dataobs-spark-metrics; do
 c=$(curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}/_count"|sed -n 's/.*"count":\([0-9]*\).*/\1/p'); [ "${c:-0}" -gt 0 ] || { echo "❌ ${idx} empty"; exit 1; }; echo "✅ ${idx} count=${c}";
done
qc=$(curl -sf "${AUTH[@]}" "${ES_HOST}/dataobs-quality/_count"|sed -n 's/.*"count":\([0-9]*\).*/\1/p'); echo "✅ dataobs-quality count=${qc:-0}"
if [ -f kibana/saved_objects/road_safety_dashboards.ndjson ]; then echo "✅ dashboards saved object exists"; else echo "❌ dashboards missing"; exit 1; fi
