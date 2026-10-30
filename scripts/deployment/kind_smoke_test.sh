#!/usr/bin/env bash
set -Eeuo pipefail
CLUSTER=${DATAOBS_KIND_CLUSTER:-dataobs-beta}; RELEASE=${DATAOBS_RELEASE:-dataobs}; NS=${DATAOBS_NAMESPACE:-dataobs-smoke}; DIAGNOSTICS=${DATAOBS_KIND_DIAGNOSTICS:-/tmp/dataobs-kind-diagnostics.txt}
cleanup(){
  rc=$?
  if command -v kubectl >/dev/null; then
    mkdir -p "$(dirname "$DIAGNOSTICS")"
    {
      echo '=== resources ==='
      kubectl -n "$NS" get all,jobs,pods -o wide || true
      echo '=== events ==='
      kubectl -n "$NS" get events --sort-by=.lastTimestamp || true
      for component in api console; do
        pod="$(kubectl -n "$NS" get pod -l "app.kubernetes.io/component=$component" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
        if [[ -n "$pod" ]]; then
          echo "=== $component logs: $pod ==="
          kubectl -n "$NS" logs "$pod" --tail=300 || true
          echo "=== $component previous logs: $pod ==="
          kubectl -n "$NS" logs "$pod" --previous --tail=300 || true
        fi
      done
    } > "$DIAGNOSTICS" 2>&1
    helm uninstall "$RELEASE" -n "$NS" >/dev/null 2>&1 || true
  fi
  exit "$rc"
}
trap cleanup EXIT
for c in kind kubectl helm; do command -v "$c" >/dev/null || { echo "SKIP (not pass): missing $c" >&2; exit 77; }; done
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --name "$CLUSTER" --wait 120s
: "${DATAOBS_SMOKE_VALUES:?Set DATAOBS_SMOKE_VALUES to digest-pinned values and a reachable test Elasticsearch; unavailable images may be disabled there}"
helm upgrade --install "$RELEASE" helm/dataobs -n "$NS" --create-namespace -f "$DATAOBS_SMOKE_VALUES" --wait --timeout 10m
kubectl -n "$NS" wait --for=condition=available deployment -l app.kubernetes.io/component=api --timeout=5m
kubectl -n "$NS" wait --for=condition=available deployment -l app.kubernetes.io/component=console --timeout=5m
old=$(kubectl -n "$NS" get pod -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}')
helm upgrade "$RELEASE" helm/dataobs -n "$NS" -f "$DATAOBS_SMOKE_VALUES" --set-string api.podAnnotations.smoke-revision="$(date +%s)" --wait --timeout 10m
if kubectl -n "$NS" get pod "$old" >/dev/null 2>&1; then echo 'rollout did not replace API pod' >&2; exit 1; fi
echo 'Local bounded smoke completed; this is not product certification.'
