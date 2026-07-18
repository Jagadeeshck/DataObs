#!/usr/bin/env bash
set -euo pipefail
SENTINEL="${POSTGRES_PASSWORD:-DATAOBS_SENTINEL_PASSWORD_DO_NOT_PERSIST}"
python -m packages.elastic_store.cli plan >/tmp/dataobs-plan.json
python -m packages.elastic_store.cli apply >/tmp/dataobs-apply.json
python -m packages.elastic_store.cli status >/tmp/dataobs-status.json
python -m services.scanner_worker.cli --config config/postgres-scanner.example.yaml print-capabilities >/tmp/dataobs-scanner-capabilities.json
if rg -n "$SENTINEL" /tmp/dataobs-*.json . --glob '!./.git/**' --glob '!docker-compose.postgres-demo.yml' --glob '!scripts/demo_postgres_vertical_slice.sh'; then
  echo "sentinel secret leaked" >&2; exit 1
fi
echo "PostgreSQL vertical slice smoke completed"
