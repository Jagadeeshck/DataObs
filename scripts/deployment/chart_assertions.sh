#!/usr/bin/env bash
set -euo pipefail
CHART=helm/dataobs; tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
helm lint "$CHART"
helm template dataobs "$CHART" -f "$CHART/values-production.yaml" >"$tmp"
for component in api console quality-worker scanner-worker monitor-runtime pathway-worker kafka-observer otel-collector; do grep -q "app.kubernetes.io/component: $component" "$tmp"; done
[[ $(grep -c '^kind: Job$' "$tmp") -eq 1 ]]
! grep -E 'image: .*:latest([[:space:]]|$)' "$tmp"
grep -q 'image: .*@sha256:' "$tmp"
grep -q '^kind: NetworkPolicy$' "$tmp"
[[ $(grep -c '^kind: PodDisruptionBudget$' "$tmp") -eq 3 ]]
helm template dataobs "$CHART" -f "$CHART/values-minimal.yaml" >"$tmp"
! grep -q 'app.kubernetes.io/component: scanner-worker' "$tmp"
! grep -qE '(plaintext-test-secret|password: [^$])' "$tmp"
printf 'chart assertions passed\n'
