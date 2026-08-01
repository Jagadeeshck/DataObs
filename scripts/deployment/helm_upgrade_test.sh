#!/usr/bin/env bash
set -Eeuo pipefail
for c in kubectl helm; do command -v "$c" >/dev/null || { echo "SKIP (not pass): missing $c" >&2; exit 77; }; done
: "${DATAOBS_UPGRADE_VALUES:?Set digest-pinned test values}"; NS=${DATAOBS_NAMESPACE:-dataobs-upgrade}; RELEASE=${DATAOBS_RELEASE:-dataobs-upgrade}; PREVIOUS_CHART=${DATAOBS_PREVIOUS_CHART:-helm/dataobs}
helm upgrade --install "$RELEASE" "$PREVIOUS_CHART" -n "$NS" --create-namespace -f "$DATAOBS_UPGRADE_VALUES" --wait --timeout 10m
helm upgrade "$RELEASE" helm/dataobs -n "$NS" -f "$DATAOBS_UPGRADE_VALUES" --wait --timeout 10m
kubectl -n "$NS" wait --for=condition=available deployment -l 'app.kubernetes.io/component in (api,console)' --timeout=5m
helm rollback "$RELEASE" 1 -n "$NS" --wait --timeout 10m
kubectl -n "$NS" wait --for=condition=available deployment -l 'app.kubernetes.io/component in (api,console)' --timeout=5m
echo 'Rollback restored Kubernetes resources only; Elasticsearch migrations were not reversed.'
