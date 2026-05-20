#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"

./scripts/verify_poc.sh

ES_HOST="${ES_HOST:-http://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PASS="${ELASTIC_PASSWORD:-${ES_PASS:-dataobs_poc_elastic}}"
AUTH=(-u "${ES_USER}:${ES_PASS}")

required=(dataobs-test-data dataobs-spark-results dataobs-quality dataobs-lineage)
for idx in "${required[@]}"; do
  count=$(curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}/_count" | sed -n 's/.*"count":\([0-9]*\).*/\1/p')
  if [ "${count:-0}" -le 0 ]; then
    echo "❌ ${idx} has zero documents"
    exit 1
  fi
  echo "✅ ${idx} count=${count}"
done

echo
echo "Kibana walkthrough:"
echo "- Observability > APM > Services > dataobs-poc-pipeline"
echo "- Analytics > Discover > dataobs-quality / dataobs-lineage"
