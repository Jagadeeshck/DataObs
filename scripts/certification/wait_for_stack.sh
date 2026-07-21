#!/usr/bin/env bash
set -Eeuo pipefail
profile="${1:-core}"; deadline=$((SECONDS + ${CERTIFICATION_READY_TIMEOUT_SECONDS:-300}))
urls=(http://127.0.0.1:19200/_cluster/health)
[[ "$profile" =~ ^(core|browser|full)$ ]] && urls+=(http://127.0.0.1:18000/health http://127.0.0.1:18080/healthz)
for url in "${urls[@]}"; do
  until curl --fail --silent --show-error "$url" >/dev/null; do
    if (( SECONDS >= deadline )); then
      docker compose -f docker-compose.certification.yml --profile "$profile" ps >&2
      exit 70
    fi
    sleep 3
  done
done
