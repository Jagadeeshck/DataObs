#!/usr/bin/env bash
set -euo pipefail

# Thin adapter to the site-specific driver installed by the protected GitHub
# environment. Infrastructure credentials and destructive implementation stay
# outside the repository; this adapter deliberately cannot simulate a pass.
phase="${1:?phase required}"
case "$phase" in
  provision|dependencies|install|security|smoke|upgrade-rollback|recovery|consolidate|verify|decision|cleanup) ;;
  *) echo "unknown hosted certification phase: $phase" >&2; exit 2 ;;
esac

driver="${DATAOBS_HOSTED_CERTIFICATION_DRIVER:-}"
if [[ -z "$driver" || ! -x "$driver" ]]; then
  echo "PENDING: protected hosted certification driver is unavailable for phase $phase" >&2
  # Cleanup is idempotent and may run after validation failed before provision.
  [[ "$phase" == cleanup ]] && exit 0
  exit 3
fi

required=(TARGET_SHA TERMINAL_MIGRATION INFRASTRUCTURE_PROFILE SYNTHETIC_MARKER EVIDENCE_DIR)
for name in "${required[@]}"; do
  [[ -n "${!name:-}" ]] || { echo "PENDING: required protected run input $name is absent" >&2; exit 3; }
done
[[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "unsafe target SHA" >&2; exit 4; }
[[ "$INFRASTRUCTURE_PROFILE" == *certification-test* && "$INFRASTRUCTURE_PROFILE" != *production* ]] || {
  echo "unsafe infrastructure profile" >&2; exit 4;
}
[[ "$SYNTHETIC_MARKER" == synthetic-* ]] || { echo "unsafe fixture marker" >&2; exit 4; }

exec "$driver" "$phase"
