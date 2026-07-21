#!/usr/bin/env bash
set -Eeuo pipefail
deadline=$((SECONDS + ${CERTIFICATION_READY_TIMEOUT_SECONDS:-300}))
compose=(docker compose -f docker-compose.certification.yml --profile cert-kafka)
while (( SECONDS < deadline )); do
  container="$(${compose[@]} ps -q kafka-observer)"
  if [[ -z "$container" ]] || [[ "$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null || true)" != true ]]; then
    ${compose[@]} logs --tail=100 kafka-observer >&2 || true
    echo 'Kafka Observer exited before readiness' >&2
    exit 70
  fi
  if ${compose[@]} exec -T kafka-observer python -m services.kafka_observer.cli collect-once --config /app/certification/config/kafka-observer.yaml >/dev/null; then
    # A successful bounded collection proves config parsing, Kafka/Elasticsearch reachability,
    # and completion of at least one checkpoint cycle.
    exit 0
  fi
  sleep 3
done
${compose[@]} logs --tail=100 kafka-observer >&2 || true
echo 'Kafka Observer did not complete a collection cycle before timeout' >&2
exit 70
