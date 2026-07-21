#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "$root/certification/evidence" "$root/certification/runtime-secrets"
password_file="$root/certification/runtime-secrets/postgres-password.txt"
# Generate into the file directly: neither the value nor a value-bearing command is logged.
python - "$password_file" <<'PY'
import secrets, sys
from pathlib import Path
path = Path(sys.argv[1])
path.write_text(secrets.token_urlsafe(32) + "\n")
path.chmod(0o600)
PY
export CERTIFICATION_POSTGRES_PASSWORD_FILE="$password_file"
printf 'CERTIFICATION_POSTGRES_PASSWORD_FILE=%q\n' "$password_file" > "$root/certification/runtime-secrets/compose.env"
chmod 600 "$root/certification/runtime-secrets/compose.env"
