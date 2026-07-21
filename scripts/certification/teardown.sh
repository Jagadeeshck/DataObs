#!/usr/bin/env bash
set -Eeuo pipefail
docker compose -f docker-compose.certification.yml --profile full down --volumes --remove-orphans
