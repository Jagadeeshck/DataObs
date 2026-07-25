#!/usr/bin/env bash
set -Eeuo pipefail
profile="${1:-core}"; deadline=$((SECONDS + ${CERTIFICATION_READY_TIMEOUT_SECONDS:-300}))
urls=(http://127.0.0.1:19200/_cluster/health)
[[ "$profile" =~ ^(core|browser-infra|cert-browser|full)$ ]] && urls+=(http://127.0.0.1:18000/health http://127.0.0.1:18080/healthz http://127.0.0.1:18080/api/health)
[[ "$profile" =~ ^(kafka|cert-kafka|full)$ ]] && urls+=(http://127.0.0.1:18081/subjects http://127.0.0.1:18083/connectors)
for url in "${urls[@]}"; do
  until curl --fail --silent --show-error "$url" >/dev/null; do
    if (( SECONDS >= deadline )); then
      docker compose -f docker-compose.certification.yml --profile "$profile" ps >&2
      docker compose -f docker-compose.certification.yml --profile "$profile" logs --tail=100 >&2
      docker network inspect certification-public certification-control certification-data >&2 || true
      df -h >&2
      (free -h || true) >&2
      exit 70
    fi
    sleep 3
  done
done

if [[ "$profile" =~ ^(kafka|cert-kafka|full)$ ]]; then
  container="$(docker compose -f docker-compose.certification.yml --profile "$profile" ps -q kafka-observer)"
  [[ -n "$container" && "$(docker inspect -f '{{.State.Running}}' "$container")" = true ]] || { echo "Kafka Observer exited during startup" >&2; exit 70; }
fi
