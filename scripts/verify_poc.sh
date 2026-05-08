#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# DataObs POC — verify Elasticsearch indices, mappings & data counts
#
# Usage:
#   ELASTIC_PASSWORD=... ./scripts/verify_poc.sh           # localhost:9200
#   ES_HOST=http://es01:9200 ./scripts/verify_poc.sh        # custom host
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

ES_HOST="${ES_HOST:-http://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PASS="${ELASTIC_PASSWORD:-${ES_PASS:-dataobs_poc_elastic}}"

AUTH=(-u "${ES_USER}:${ES_PASS}")
JQ=$(command -v jq || true)

# Indices we expect after a successful POC run.
INDICES=(
  "dataobs-test-data"
  "dataobs-spark-results"
  "dataobs-assets"
  "dataobs-quality"
  "dataobs-freshness"
  "dataobs-volume"
  "dataobs-schema"
  "dataobs-lineage"
  "dataobs-alerts"
)

# OTel-fed indices (may be data streams) — counted but not required to pass.
OTEL_INDICES=(
  "dataobs-otel-traces"
  "dataobs-otel-metrics"
  "dataobs-otel-logs"
)

echo "════════════════════════════════════════════════════════════════"
echo " DataObs POC verification — ${ES_HOST}"
echo "════════════════════════════════════════════════════════════════"

# ── Cluster health ─────────────────────────────────────────────────
echo
echo "[1/4] Cluster health"
HEALTH=$(curl -sf "${AUTH[@]}" "${ES_HOST}/_cluster/health")
echo "${HEALTH}"
NODES=$(echo "${HEALTH}" | sed -n 's/.*"number_of_nodes":\([0-9]*\).*/\1/p')
STATUS=$(echo "${HEALTH}" | sed -n 's/.*"status":"\([a-z]*\)".*/\1/p')
echo "→ status=${STATUS} nodes=${NODES}"
if [ "${STATUS}" = "red" ]; then
  echo "FAIL: cluster is RED"
  exit 1
fi

# ── Node listing ───────────────────────────────────────────────────
echo
echo "[2/4] Nodes"
curl -sf "${AUTH[@]}" "${ES_HOST}/_cat/nodes?v&h=name,node.role,heap.percent,ram.percent,master"

# ── Index/data-doc check ──────────────────────────────────────────
echo
echo "[3/4] POC indices, doc counts and mappings"
fail=0
for idx in "${INDICES[@]}"; do
  if ! curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}" >/dev/null; then
    echo "  ❌ ${idx} — does not exist"
    fail=$((fail+1))
    continue
  fi
  COUNT=$(curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}/_count" \
    | sed -n 's/.*"count":\([0-9]*\).*/\1/p')
  COUNT=${COUNT:-0}
  MAPPING_FIELDS=$(curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}/_mapping" \
    | tr ',' '\n' | grep -c '"type"' || true)
  printf "  ✅ %-28s count=%-6s mapped_fields=%s\n" "${idx}" "${COUNT}" "${MAPPING_FIELDS}"
done

echo
echo "  -- OTel indices (informational) --"
for idx in "${OTEL_INDICES[@]}"; do
  COUNT=$(curl -sf "${AUTH[@]}" "${ES_HOST}/${idx}/_count" 2>/dev/null \
    | sed -n 's/.*"count":\([0-9]*\).*/\1/p' || true)
  printf "  ℹ️  %-28s count=%s\n" "${idx}" "${COUNT:-missing}"
done

# ── Templates ─────────────────────────────────────────────────────
echo
echo "[4/4] POC index templates"
TEMPLATES=$(curl -sf "${AUTH[@]}" "${ES_HOST}/_index_template" \
  | tr ',' '\n' | sed -n 's/.*"name":"\(dataobs-[^"]*\)".*/\1/p' | sort -u)
echo "${TEMPLATES}" | sed 's/^/  /'

echo
if [ "${fail}" -eq 0 ]; then
  echo "✅ PASS — all required POC indices exist with mappings."
  exit 0
fi
echo "❌ FAIL — ${fail} expected indices missing. Run the pipeline first:"
echo "   docker compose -f docker-compose.poc.yml --env-file .env.poc.local run --rm pipeline"
exit 1
