#!/usr/bin/env bash
set -euo pipefail
compose=(docker compose -f docker-compose.kafka-dsm-demo.yml)
"${compose[@]}" config >/dev/null
printf 'Kafka DSM demo configuration is valid.\n'
printf 'Start the ci profile, apply migration 0004, then run tests/integration/kafka_data_streams_monitoring.\n'
printf 'Safety invariant: payload_capture=false; optional Kafka Read=false.\n'
