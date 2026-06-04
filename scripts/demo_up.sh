#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.poc.yml --env-file .env.poc)

echo "[demo_up] Resetting stale containers (safe stop)..."
"${COMPOSE[@]}" down --remove-orphans || true

echo "[demo_up] Starting default POC services (Elastic Agent/APM path)..."
"${COMPOSE[@]}" up -d es01 kibana fleet-server elastic-agent

echo "[demo_up] Waiting for health checks..."
for svc in es01 kibana fleet-server elastic-agent; do
  cid=$("${COMPOSE[@]}" ps -q "$svc")
  [ -n "$cid" ] || continue
  for i in {1..60}; do
    state=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid")
    if [ "$state" = "healthy" ] || [ "$state" = "running" ]; then
      echo "  ✅ $svc: $state"
      break
    fi
    if [ "$i" -eq 60 ]; then
      echo "  ❌ $svc did not become healthy"
      exit 1
    fi
    sleep 3
  done
done

echo
echo "Kibana: http://localhost:5601"
echo "Login: elastic / ${ELASTIC_PASSWORD:-dataobs_poc_elastic}"
echo
echo "DataObs Docker DNS endpoints (from containers on the dataobs-poc network):"
echo "  APM intake:     http://dataobs-poc-elastic-agent:8200"
echo "  Elasticsearch:  http://dataobs-poc-es01:9200"
echo "  Kibana:         http://dataobs-poc-kibana:5601"
echo "  Fleet Server:   http://dataobs-poc-fleet-server:8220"
echo
echo "Connect an external app container to DataObs DNS with:"
echo "  ./scripts/connect_external_stack.sh <container-name>"
echo
echo "Reminder: APM agents use port 8200; Fleet enrolment/check-in uses port 8220."
