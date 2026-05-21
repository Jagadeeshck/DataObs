#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"; cd "$ROOT"
./scripts/verify_poc.sh
python scripts/validate_kibana_saved_objects.py
ES_HOST="${ES_HOST:-http://localhost:9200}"; ES_USER="${ES_USER:-elastic}"; ES_PASS="${ELASTIC_PASSWORD:-${ES_PASS:-dataobs_poc_elastic}}"
KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"; KIBANA_USER="${KIBANA_USERNAME:-${ES_USER}}"; KIBANA_PASS="${KIBANA_PASSWORD:-${ES_PASS}}"
AUTH=(-u "${ES_USER}:${ES_PASS}"); KAUTH=(-u "${KIBANA_USER}:${KIBANA_PASS}")
for idx in dataobs-quality dataobs-alerts dataobs-freshness dataobs-volume dataobs-schema dataobs-lineage dataobs-spark-metrics dataobs-rs-accident-facts dataobs-rs-authority-risk-summary dataobs-rs-road-risk-summary dataobs-rs-vehicle-risk-summary dataobs-rs-casualty-severity-summary; do
  if ! curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}" >/dev/null; then
    echo "❌ index missing: ${idx} (${ES_HOST}/${idx})"
    exit 1
  fi
  c=$(curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}/_count"|sed -n 's/.*"count":\([0-9]*\).*/\1/p')
  [ "${c:-0}" -gt 0 ] || { echo "❌ index has zero docs: ${idx} (${ES_HOST}/${idx}/_count)"; exit 1; }
  echo "✅ index has docs: ${idx} count=${c}"
done

quality_bad=$(curl -sf "${AUTH[@]}" -H 'Content-Type: application/json' "${ES_HOST}/dataobs-quality/_count" -d '{"query":{"terms":{"status":["fail","warn"]}}}'|sed -n 's/.*"count":\([0-9]*\).*/\1/p')
[ "${quality_bad:-0}" -gt 0 ] || { echo "❌ dataobs-quality has no fail/warn records"; exit 1; }
echo "✅ dataobs-quality fail/warn count=${quality_bad}"

alerts_count=$(curl -sf "${AUTH[@]}" "${ES_HOST}/dataobs-alerts/_count"|sed -n 's/.*"count":\([0-9]*\).*/\1/p')
[ "${alerts_count:-0}" -gt 0 ] || { echo "❌ dataobs-alerts has no records"; exit 1; }
echo "✅ dataobs-alerts records=${alerts_count}"

spark_count=$(curl -sf "${AUTH[@]}" "${ES_HOST}/dataobs-spark-metrics/_count"|sed -n 's/.*"count":\([0-9]*\).*/\1/p')
[ "${spark_count:-0}" -gt 0 ] || { echo "❌ dataobs-spark-metrics has no records"; exit 1; }
echo "✅ dataobs-spark-metrics records=${spark_count}"
expected=("DataObs Road Safety Executive Overview" "Data Quality & Bad Data Detection" "Freshness / Volume / Schema Drift" "Lineage & Impact" "Spark Pipeline Performance")
dash_json=$(curl -sf "${KAUTH[@]}" -H 'kbn-xsrf: true' "${KIBANA_URL}/api/saved_objects/_find?type=dashboard&per_page=200")
for t in "${expected[@]}"; do
  entry=$(echo "$dash_json" | tr '{' '\n' | grep -F "\"title\":\"${t}\"" || true)
  [ -n "$entry" ] || { echo "❌ dashboard missing: ${t}"; exit 1; }
  echo "✅ dashboard exists: ${t} (show KPIs + charts + tables)"
done

cat <<EOF

Debug commands:
- docker logs dataobs-poc-pipeline 2>&1 | tail -100
- curl -u ${ES_USER}:${ES_PASS} ${ES_HOST}/_cat/indices/dataobs-rs-*?v
- curl -u ${ES_USER}:${ES_PASS} ${ES_HOST}/dataobs-spark-metrics/_count
EOF
