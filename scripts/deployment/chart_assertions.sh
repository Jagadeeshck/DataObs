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
python - "$tmp" <<'PY'
import re, sys, yaml
docs=[d for d in yaml.safe_load_all(open(sys.argv[1])) if d]
errors=[]
workloads={"Deployment","StatefulSet","DaemonSet","Job"}
for doc in docs:
  kind=doc.get("kind")
  spec=doc.get("spec",{})
  if spec.get("hostNetwork") or spec.get("hostPID") or spec.get("hostIPC"):
    errors.append(f"{kind}/{doc['metadata']['name']}: host namespaces are forbidden")
  if kind not in workloads: continue
  pod=spec.get("template",{}).get("spec",spec)
  if pod.get("hostNetwork") or pod.get("hostPID") or pod.get("hostIPC"):
    errors.append(f"{kind}/{doc['metadata']['name']}: host namespaces are forbidden")
  if pod.get("securityContext",{}).get("seccompProfile",{}).get("type") != "RuntimeDefault":
    errors.append(f"{kind}/{doc['metadata']['name']}: seccomp RuntimeDefault is required")
  for container in pod.get("containers",[]):
    label=f"{kind}/{doc['metadata']['name']}:{container.get('name')}"
    image=container.get("image","")
    if "@sha256:" not in image: errors.append(f"{label}: image is not digest pinned")
    security=container.get("securityContext",{})
    if security.get("privileged") is True: errors.append(f"{label}: privileged is forbidden")
    if security.get("runAsNonRoot") is not True: errors.append(f"{label}: runAsNonRoot is required")
    if security.get("readOnlyRootFilesystem") is not True: errors.append(f"{label}: read-only root is required")
    if security.get("capabilities",{}).get("drop") != ["ALL"]: errors.append(f"{label}: all capabilities must be dropped")
    resources=container.get("resources",{})
    if not resources.get("requests") or not resources.get("limits"): errors.append(f"{label}: requests and limits required")
    if kind != "Job" and not all(container.get(p) for p in ("livenessProbe","readinessProbe","startupProbe")):
      errors.append(f"{label}: liveness, readiness and startup probes required")
text=open(sys.argv[1]).read()
if re.search(r"(?i)(password|client_secret)\s*:\s*['\"]?(?!\$|<|$)[^\s{}]+", text):
  errors.append("rendered manifest contains a plaintext password-like value")
if any(d.get("kind") in {"Elasticsearch","Keycloak"} or "elasticsearch" in d.get("metadata",{}).get("name","").lower() for d in docs):
  errors.append("chart must not deploy Elasticsearch or an identity provider")
if errors: raise SystemExit("\n".join(sorted(errors)))
PY
helm template dataobs "$CHART" -f "$CHART/values-minimal.yaml" >"$tmp"
! grep -q 'app.kubernetes.io/component: scanner-worker' "$tmp"
! grep -qE '(plaintext-test-secret|password: [^$])' "$tmp"
! grep -q 'app.kubernetes.io/component: elasticsearch' "$tmp"
printf 'chart assertions passed\n'
