#!/usr/bin/env bash
set -Eeuo pipefail
export ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://127.0.0.1:19200}"
python -m packages.elastic_store.cli apply
python -m packages.elastic_store.cli status
