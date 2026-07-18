#!/usr/bin/env bash
set -euo pipefail
for url in http://localhost:9200/_cluster/health http://localhost:8000/health http://localhost:8080/healthz; do timeout 180 bash -c "until curl -fsS '$url' >/dev/null; do sleep 3; done"; done
./bin/dataobs elastic apply
python scripts/seed_console_demo.py
curl -fsS -H 'X-DataObs-Tenant: acme-retail' 'http://localhost:8000/api/v1/command-center?environment=production' >/tmp/console-summary.json
curl -fsS -H 'X-DataObs-Tenant: acme-retail' 'http://localhost:8000/api/v1/topology?environment=production' >/tmp/console-topology.json
curl -fsSN --max-time 3 -H 'X-DataObs-Tenant: acme-retail' 'http://localhost:8000/api/v1/events/stream?environment=production' | rg 'event: keepalive'
! curl -fsS -H 'X-DataObs-Tenant: acme-retail' 'http://localhost:8000/api/v1/command-center?environment=staging' | rg 'northstar'
! rg -n 'DATAOBS_SENTINEL_PASSWORD_DO_NOT_PERSIST' ui/dataobs-console/dist /tmp/console-*.json
printf 'Console: http://localhost:8080\n'
