#!/usr/bin/env bash
set -euo pipefail

DATAOBS_NETWORK="${DATAOBS_NETWORK:-dataobs-poc}"

print_usage() {
  cat <<'USAGE'
Usage: DATAOBS_NETWORK=dataobs-poc ./scripts/connect_external_stack.sh <container-name> [container-name ...]

Connect one or more already-running external Docker containers to the DataObs POC
network so they can resolve stable DataObs container DNS names.
USAGE
}

print_endpoints() {
  cat <<'ENDPOINTS'

DataObs Docker DNS endpoints (from connected external containers):
  APM intake:     http://dataobs-poc-elastic-agent:8200
  Elasticsearch:  http://dataobs-poc-es01:9200
  Kibana:         http://dataobs-poc-kibana:5601
  Fleet Server:   http://dataobs-poc-fleet-server:8220

Example Elastic APM environment for an external app container:
  ELASTIC_APM_SERVER_URL=http://dataobs-poc-elastic-agent:8200
  ELASTIC_APM_SECRET_TOKEN=dataobs_poc_apm_token
  ELASTIC_APM_SERVICE_NAME=<your-service-name>
  ELASTIC_APM_ENVIRONMENT=poc

Note: APM agents use port 8200. Fleet enrolment/check-in uses port 8220.
ENDPOINTS
}

container_connected_to_network() {
  local container="$1"
  docker network inspect \
    --format '{{range .Containers}}{{.Name}}{{"\n"}}{{end}}' \
    "$DATAOBS_NETWORK" | grep -Fxq -- "$container"
}

if [ "$#" -lt 1 ]; then
  print_usage >&2
  exit 2
fi

if ! docker network inspect "$DATAOBS_NETWORK" >/dev/null 2>&1; then
  echo "ERROR: Docker network '$DATAOBS_NETWORK' does not exist." >&2
  echo "Start the DataObs POC first, for example: ./scripts/demo_up.sh" >&2
  exit 1
fi

for container in "$@"; do
  if ! docker container inspect "$container" >/dev/null 2>&1; then
    echo "ERROR: Docker container '$container' does not exist." >&2
    exit 1
  fi

done

for container in "$@"; do
  if container_connected_to_network "$container"; then
    echo "[dataobs] '$container' is already connected to '$DATAOBS_NETWORK'."
  else
    echo "[dataobs] Connecting '$container' to '$DATAOBS_NETWORK'..."
    docker network connect "$DATAOBS_NETWORK" "$container"
    echo "[dataobs] Connected '$container' to '$DATAOBS_NETWORK'."
  fi
done

print_endpoints
