#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python -m json.tool "$root/certification/fixtures/tenants/manifest.json" >/dev/null
# Repository seeders use deterministic document IDs and are therefore idempotent.
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-http://127.0.0.1:19200}" python "$root/scripts/seed_console_demo.py"
