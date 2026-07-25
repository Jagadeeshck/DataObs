#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
out="$root/certification/evidence"
mkdir -p "$out"
docker compose -f "$root/docker-compose.certification.yml" --profile "${CERTIFICATION_PROFILE:-full}" config > "$out/compose-config.txt"
docker compose -f "$root/docker-compose.certification.yml" --profile "${CERTIFICATION_PROFILE:-full}" ps --format json > "$out/service-health.json"
python "$root/scripts/certification/redact_artifacts.py" "$out"
python "$root/scripts/certification/verify_artifacts.py" "$out" --sentinels-only
python "$root/scripts/certification/build_manifest.py" "$out"
python "$root/scripts/certification/verify_artifacts.py" "$out"
