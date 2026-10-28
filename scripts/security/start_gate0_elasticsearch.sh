#!/usr/bin/env bash
# Only for a disposable hosted runner, with real HTTP TLS and basic authentication.
set -Eeuo pipefail
: "${RUNNER_TEMP:?}"
: "${GITHUB_ENV:?}"
work="$RUNNER_TEMP/gate0-secured-es"
mkdir -p "$work/certs"
umask 077
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 1 \
  -subj /CN=localhost -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' \
  -keyout "$work/certs/server.key" -out "$work/certs/server.crt" 2>/dev/null
# The container runs as uid 1000. Public cert is not a secret; key is ephemeral.
chmod 755 "$work" "$work/certs"
chmod 644 "$work/certs/server.crt"
chmod 644 "$work/certs/server.key"
password=$(openssl rand -hex 24)
printf '::add-mask::%s\n' "$password"
printf 'ELASTIC_PASSWORD=%s\n' "$password" > "$work/es.env"
docker run -d --name dataobs-gate0-secured-es --env-file "$work/es.env" \
  -p 127.0.0.1:9200:9200 -v "$work/certs:/usr/share/elasticsearch/config/certs:ro" \
  -e discovery.type=single-node -e xpack.security.enabled=true \
  -e xpack.security.http.ssl.enabled=true \
  -e xpack.security.http.ssl.key=certs/server.key -e xpack.security.http.ssl.certificate=certs/server.crt \
  -e ES_JAVA_OPTS='-Xms1g -Xmx1g' docker.elastic.co/elasticsearch/elasticsearch:9.4.2
export ELASTICSEARCH_URL=https://localhost:9200 ELASTICSEARCH_USER=elastic ELASTICSEARCH_PASSWORD="$password" ELASTICSEARCH_CA_CERTS="$work/certs/server.crt"
python - <<'PY'
import os, time
from packages.elastic_store.client import make_client
es = make_client()
for _ in range(90):
    try:
        assert es.info()['version']['number'] == '9.4.2'
        assert es.cluster.health(wait_for_status='yellow', timeout='2s')['status'] in {'yellow', 'green'}
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit('secured TLS Elasticsearch did not become ready')
with open(os.environ['GITHUB_ENV'], 'a') as output:
    for name in ('ELASTICSEARCH_URL', 'ELASTICSEARCH_USER', 'ELASTICSEARCH_PASSWORD', 'ELASTICSEARCH_CA_CERTS'):
        output.write(name + '=' + os.environ[name] + '\n')
PY
