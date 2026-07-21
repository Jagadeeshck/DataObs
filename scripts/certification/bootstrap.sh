#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "$root/certification/evidence"
# Values are ephemeral inputs and deliberately never emitted to logs or reports.
export DATAOBS_CERT_DB_PASSWORD="${DATAOBS_CERT_DB_PASSWORD:-$(python -c 'import secrets; print(secrets.token_urlsafe(24))')}"
