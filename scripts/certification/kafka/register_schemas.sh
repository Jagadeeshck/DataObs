#!/usr/bin/env bash
set -Eeuo pipefail
curl -fsS -X POST -H 'Content-Type: application/vnd.schemaregistry.v1+json' "${SCHEMA_REGISTRY_URL}/subjects/certification-orders-value/versions" --data '{"schema":"{\"type\":\"record\",\"name\":\"Order\",\"fields\":[{\"name\":\"id\",\"type\":\"string\"}]}"}' >/dev/null
