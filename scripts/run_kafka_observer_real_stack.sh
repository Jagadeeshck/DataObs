#!/usr/bin/env bash
set -euo pipefail
docker compose -f docker-compose.kafka-observer-real-stack.yml run --rm kafka-observer collect-once --config /app/config/kafka-observer.example.yaml
docker compose -f docker-compose.kafka-observer-real-stack.yml run --rm kafka-observer offsets --config /app/config/kafka-observer.example.yaml
