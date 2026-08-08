#!/usr/bin/env bash
set -euo pipefail
# Site-specific protected test environments provide this hook. Absence fails closed.
phase="${1:?phase required}"
case "$phase" in deploy|seed|baseline|load|autoscale|worker-scale|pod-failure|node-failure|soak|cleanup) ;; *) echo "unknown phase" >&2; exit 2;; esac
if [[ -z "${DATAOBS_SCALE_CERTIFICATION_DRIVER:-}" || ! -x "${DATAOBS_SCALE_CERTIFICATION_DRIVER:-}" ]]; then
  echo "No protected disposable-test certification driver configured for phase $phase" >&2
  [[ "$phase" == cleanup ]] && exit 0
  exit 3
fi
exec "$DATAOBS_SCALE_CERTIFICATION_DRIVER" "$phase"
