#!/usr/bin/env bash
set -euo pipefail
CHART=helm/dataobs; tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
helm lint "$CHART"
helm template dataobs "$CHART" -f "$CHART/values-production.yaml" >"$tmp"
for component in api console quality-worker scanner-worker monitor-runtime pathway-worker kafka-observer otel-collector; do grep -q "app.kubernetes.io/component: $component" "$tmp"; done
[[ $(grep -c '^kind: Job$' "$tmp") -eq 1 ]]
! grep -E 'image: .*:latest([[:space:]]|$)' "$tmp"
images=$(grep -c '^[[:space:]]*image: ' "$tmp")
digests=$(grep -c '^[[:space:]]*image: .*@sha256:[0-9a-f]\{64\}' "$tmp")
[[ "$images" -eq "$digests" ]]
! grep -Eq '^[[:space:]]*(privileged|hostNetwork|hostPID|hostIPC):[[:space:]]*true' "$tmp"
! grep -Eq '^[[:space:]]*readOnlyRootFilesystem:[[:space:]]*false' "$tmp"
! grep -Eiq '^[[:space:]]*(password|clientSecret|token):[[:space:]]+[^$<{[:space:]]' "$tmp"
grep -q 'runAsNonRoot: true' "$tmp"
grep -q 'readOnlyRootFilesystem: true' "$tmp"
grep -q 'seccompProfile:' "$tmp"
grep -q 'drop:' "$tmp" && grep -q -- '- ALL' "$tmp"
for required in 'requests:' 'limits:' 'livenessProbe:' 'readinessProbe:' 'startupProbe:'; do grep -q "$required" "$tmp"; done
grep -q '^kind: NetworkPolicy$' "$tmp"
[[ $(grep -c '^kind: PodDisruptionBudget$' "$tmp") -eq 3 ]]
helm template dataobs "$CHART" -f "$CHART/values-minimal.yaml" >"$tmp"
! grep -q 'app.kubernetes.io/component: scanner-worker' "$tmp"
! grep -qE '(plaintext-test-secret|password: [^$])' "$tmp"
! grep -q 'app.kubernetes.io/component: elasticsearch' "$tmp"
printf 'chart assertions passed\n'
