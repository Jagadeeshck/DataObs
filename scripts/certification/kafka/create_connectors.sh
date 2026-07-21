#!/usr/bin/env bash
set -Eeuo pipefail
curl -fsS "${CONNECT_URL}/connectors" >/dev/null
