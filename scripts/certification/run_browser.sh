#!/usr/bin/env bash
set -Eeuo pipefail
(cd ui/dataobs-console && pnpm playwright test e2e/certification)
