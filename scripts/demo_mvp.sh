#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${DATAOBS_MVP_ENV_FILE:-$ROOT/.env.mvp}"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT/docker-compose.mvp.yml")

usage() {
  cat <<'EOF'
Usage: scripts/demo_mvp.sh <config|up|verify|status|logs|down>

  config  Validate the resolved Compose model without starting containers.
  up      Build and start the bounded demo, then execute verification.
  verify  Verify health, identity context, seeded summary, and tenant isolation.
  status  Show the current service state.
  logs    Show the most recent bounded service logs.
  down    Stop containers while retaining the Elasticsearch volume.
EOF
}

require_runtime() {
  command -v docker >/dev/null || { echo "docker is required" >&2; exit 2; }
  docker compose version >/dev/null || { echo "docker compose v2 is required" >&2; exit 2; }
  command -v curl >/dev/null || { echo "curl is required" >&2; exit 2; }
  command -v python >/dev/null || { echo "python is required" >&2; exit 2; }
  [[ -f "$ENV_FILE" ]] || {
    echo "missing $ENV_FILE; copy .env.mvp.example and replace both placeholders" >&2
    exit 2
  }
  if grep -q 'replace-with-' "$ENV_FILE"; then
    echo "$ENV_FILE still contains example placeholders" >&2
    exit 2
  fi
}

wait_url() {
  local name="$1" url="$2" deadline=$((SECONDS + 300))
  until curl --fail --silent --show-error --max-time 5 "$url" >/dev/null; do
    if (( SECONDS >= deadline )); then
      echo "timed out waiting for $name at $url" >&2
      "${COMPOSE[@]}" ps >&2 || true
      "${COMPOSE[@]}" logs --tail 100 >&2 || true
      return 1
    fi
    sleep 2
  done
}

verify() {
  wait_url "API readiness" "http://127.0.0.1:8080/readyz"
  wait_url "Console" "http://127.0.0.1:3000/healthz"

  local tmp
  tmp="$(mktemp -d)"
  trap 'find "$tmp" -type f -delete; rmdir "$tmp"' RETURN
  curl --fail --silent --show-error \
    http://127.0.0.1:3000/api/v1/auth/me >"$tmp/identity.json"
  curl --fail --silent --show-error \
    -H 'X-DataObs-Tenant: acme-retail' \
    'http://127.0.0.1:3000/api/v1/command-center?environment=production' >"$tmp/summary.json"
  curl --fail --silent --show-error \
    -H 'X-DataObs-Tenant: acme-retail' \
    'http://127.0.0.1:3000/api/v1/topology?environment=production' >"$tmp/topology.json"

  python - "$tmp" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
identity = json.loads((root / "identity.json").read_text())
summary = json.loads((root / "summary.json").read_text())
topology = json.loads((root / "topology.json").read_text())
access = identity.get("authorised_access", [])
assert access == [{"tenant_id": "acme-retail", "environments": ["production"]}], access
assert summary.get("overall_health") == "critical", summary
nodes = topology.get("nodes", [])
assert len(nodes) == 5, nodes
serialized = json.dumps({"identity": identity, "summary": summary, "topology": topology})
assert "northstar" not in serialized, "tenant isolation failed"
print("demo verification passed: identity, summary, topology, and tenant isolation")
PY
  printf '\nDemo ready:\n  Console: http://localhost:3000\n  API:     http://localhost:8080\n'
}

require_runtime
case "${1:-}" in
  config) "${COMPOSE[@]}" config >/dev/null; echo "MVP Compose configuration is valid" ;;
  up)
    "${COMPOSE[@]}" config >/dev/null
    "${COMPOSE[@]}" up --build --detach
    verify
    ;;
  verify) verify ;;
  status) "${COMPOSE[@]}" ps ;;
  logs) "${COMPOSE[@]}" logs --tail "${DATAOBS_MVP_LOG_LINES:-100}" ;;
  down) "${COMPOSE[@]}" down ;;
  *) usage; exit 2 ;;
esac

