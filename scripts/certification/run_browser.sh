#!/usr/bin/env bash
set -Eeuo pipefail
base_url="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:18080}"
curl --connect-timeout 5 --max-time 15 -fsS "$base_url/healthz" >/dev/null
curl --connect-timeout 5 --max-time 15 -fsS "$base_url/api/health" >/dev/null
export PLAYWRIGHT_BASE_URL="$base_url"
(cd ui/dataobs-console && pnpm playwright test --config=playwright.certification.config.ts)
