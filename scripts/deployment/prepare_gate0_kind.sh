#!/usr/bin/env bash
# Disposable, non-publishable registry and cluster. Never use production credentials.
set -Eeuo pipefail
: "${GITHUB_SHA:?exact workflow SHA required}"
: "${RUNNER_TEMP:?isolated runner temporary directory required}"
[[ "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]
[[ $(git rev-parse HEAD) == "$GITHUB_SHA" ]]
for tool in docker kind kubectl helm python; do command -v "$tool" >/dev/null; done
work="$RUNNER_TEMP/dataobs-gate0"
mkdir -p "$work" gate0-packaging-evidence
export DATAOBS_KIND_CLUSTER=dataobs-gate0
# Registry traffic is HTTP only on this disposable Docker network; runtime image
# references still use real registry manifest digests, never structural digests.
docker run -d --restart=no -p 127.0.0.1:5001:5000 --name dataobs-gate0-registry registry:2.8.3
cat > "$work/kind.yaml" <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
containerdConfigPatches:
- |-
  [plugins."io.containerd.grpc.v1.cri".registry.mirrors."dataobs-gate0-registry:5000"]
    endpoint = ["http://dataobs-gate0-registry:5000"]
nodes:
- role: control-plane
YAML
kind create cluster --name "$DATAOBS_KIND_CLUSTER" --image kindest/node:v1.30.13 --config "$work/kind.yaml" --wait 120s
docker network connect kind dataobs-gate0-registry
for component in api console; do
  context=.; file=Dockerfile.api
  if [[ "$component" == console ]]; then context=ui/dataobs-console; file=ui/dataobs-console/Dockerfile; fi
  docker build -f "$file" -t "127.0.0.1:5001/dataobs-$component:$GITHUB_SHA" "$context"
  docker push "127.0.0.1:5001/dataobs-$component:$GITHUB_SHA" > "gate0-packaging-evidence/$component-push.log"
  docker image inspect "127.0.0.1:5001/dataobs-$component:$GITHUB_SHA" --format '{{json .RepoDigests}}' > "$work/$component-digests.json"
done
kubectl create namespace dataobs-smoke
kubectl create namespace dataobs-upgrade
# A fresh, authenticated ES container on the Kind network is reachable by node IP.
# Credentials are generated locally, masked, kept out of values and artifacts.
password=$(openssl rand -hex 24)
printf '::add-mask::%s\n' "$password"
printf 'ELASTIC_PASSWORD=%s\n' "$password" > "$work/es.env"
chmod 600 "$work/es.env"
docker run -d --name dataobs-gate0-es --network kind --env-file "$work/es.env" \
  -e discovery.type=single-node -e xpack.security.enabled=true \
  -e xpack.security.http.ssl.enabled=false -e ES_JAVA_OPTS='-Xms1g -Xmx1g' \
  docker.elastic.co/elasticsearch/elasticsearch:9.4.2
es_ip=$(docker inspect dataobs-gate0-es --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
# Local HTTP is an explicit disposable smoke profile, not TLS certification.
ready=false
for _ in {1..90}; do
  if docker exec dataobs-gate0-es sh -c 'curl -fsS -u "elastic:$ELASTIC_PASSWORD" localhost:9200/_cluster/health?wait_for_status=yellow' > "$work/es-health.json"; then ready=true; break; fi
  sleep 2
done
[[ "$ready" == true ]]
for namespace in dataobs-smoke dataobs-upgrade; do
  kubectl -n "$namespace" create secret generic dataobs-elasticsearch --from-literal=username=elastic --from-literal=password="$password"
  kubectl -n "$namespace" create secret generic dataobs-api --from-literal=cursor-secret="$(openssl rand -hex 32)" --from-literal=signing-secret="$(openssl rand -hex 32)" --from-literal=encryption-key="$(openssl rand -hex 32)" --from-literal=api-token="$(openssl rand -hex 32)"
done
export GATE0_WORK="$work" GATE0_ES_IP="$es_ip"
python - <<'PY'
import json, os, pathlib, yaml
work = pathlib.Path(os.environ['GATE0_WORK'])
images = {}
for name in ('api', 'console'):
    refs = json.loads((work / f'{name}-digests.json').read_text())
    digest = next(r.split('@', 1)[1] for r in refs if r.startswith('127.0.0.1:5001/'))
    images[name] = {'image': {'repository': f'dataobs-{name}', 'digest': digest}, 'replicaCount': 1, 'pdb': {'enabled': False}}
values = {
    'global': {'environment': 'test', 'imageRegistry': 'dataobs-gate0-registry:5000',
               'podSecurityContext': {'runAsNonRoot': True, 'runAsUser': 1000, 'runAsGroup': 1000, 'fsGroup': 1000, 'seccompProfile': {'type': 'RuntimeDefault'}}},
    **images,
    'migrationJob': {'image': images['api']['image']},
    'external': {'elasticsearch': {'url': f"http://{os.environ['GATE0_ES_IP']}:9200"}},
    'networkPolicy': {'enabled': True, 'additionalEgressCIDRs': [os.environ['GATE0_ES_IP'] + '/32']},
    **{name: {'enabled': False} for name in ('qualityWorker', 'scannerWorker', 'monitorRuntime', 'pathwayWorker', 'kafkaObserver', 'otelCollector')},
}
values['api']['env'] = [
    {'name': 'DATAOBS_ENV', 'value': 'test'},
    {'name': 'DATAOBS_AUTH_PROVIDER', 'value': 'token'},
    {'name': 'DATAOBS_ALLOW_UNAUTHENTICATED_DEV', 'value': 'false'},
    {'name': 'API_TOKEN', 'valueFrom': {'secretKeyRef': {'name': 'dataobs-api', 'key': 'api-token'}}},
]
(work / 'values.yaml').write_text(yaml.safe_dump(values))
pathlib.Path('gate0-packaging-evidence/kind-image-identities.json').write_text(json.dumps({'producer_sha': os.environ['GITHUB_SHA'], 'images': images, 'scope': 'disposable-non-publishable'}, indent=2))
PY
printf 'DATAOBS_KIND_CLUSTER=%s\nDATAOBS_SMOKE_VALUES=%s\nDATAOBS_UPGRADE_VALUES=%s\n' "$DATAOBS_KIND_CLUSTER" "$work/values.yaml" "$work/values.yaml" >> "$GITHUB_ENV"
