#!/usr/bin/env bash
set -euo pipefail

cat <<'ENDPOINTS'
DataObs POC endpoints
=====================

Internal Docker DNS endpoints (from containers on the dataobs-poc network):
  APM intake:     http://dataobs-poc-elastic-agent:8200
  Elasticsearch:  http://dataobs-poc-es01:9200
  Kibana:         http://dataobs-poc-kibana:5601
  Fleet Server:   http://dataobs-poc-fleet-server:8220

Local host/browser endpoints (from your workstation):
  Elasticsearch:  http://localhost:9200
  Kibana:         http://localhost:5601
  APM intake:     http://localhost:8200
  Fleet Server:   http://localhost:8220

Connect an external Compose app container to DataObs DNS:
  ./scripts/connect_external_stack.sh <container-name>

Override the DataObs network name if needed:
  DATAOBS_NETWORK=<network-name> ./scripts/connect_external_stack.sh <container-name>

Remember: APM agents send telemetry to port 8200; Fleet enrolment/check-in uses port 8220.
ENDPOINTS
