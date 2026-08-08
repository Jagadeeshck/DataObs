#!/usr/bin/env bash
set -euo pipefail

# Adapter for a protected, site-specific driver.  The existing performance
# harness remains the workload generator; this adapter only orchestrates DR
# faults and evidence collection.
phase="${1:?phase required}"
case "$phase" in
  deploy|seed|baseline|elasticsearch-faults|oidc-faults|otlp-faults|upgrade|rollback|backup|destructive-restore|recovery-measurement|dr-rehearsal|multi-installation-isolation|verify|cleanup) ;;
  *) echo "unknown DR certification phase: $phase" >&2; exit 2 ;;
esac

driver="${DATAOBS_DR_CERTIFICATION_DRIVER:-}"
if [[ -z "$driver" || ! -x "$driver" ]]; then
  echo "No protected disposable-test DR certification driver configured for phase $phase" >&2
  [[ "$phase" == cleanup ]] && exit 0
  exit 3
fi
exec "$driver" "$phase"
