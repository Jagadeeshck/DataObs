#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# DataObs POC — static validation of docker-compose.poc.yml + .env.poc
#
# Verifies:
#   1. docker-compose.poc.yml is syntactically valid YAML.
#   2. Every host referenced in OTEL_*_ENDPOINT / -Dotel.*.endpoint /
#      ELASTICSEARCH_URL / ELASTICHOST / KIBANA_URL maps to a real
#      compose service name (or one of its declared network aliases).
#   3. .env.poc parses cleanly and its OTEL endpoint host is also a
#      resolvable compose service.
#
# Run this in CI / pre-push to catch regressions like the
# NameResolutionError("Failed to resolve 'otel-collector'") issue
# where an OTEL endpoint pointed at a name no service answered to.
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.poc.yml"
ENV_FILE="${REPO_ROOT}/.env.poc"

PY=$(command -v python3 || command -v python || true)
if [ -z "${PY}" ]; then
  echo "ERROR: python3 (or python) is required to validate YAML." >&2
  exit 2
fi

"${PY}" - "${COMPOSE_FILE}" "${ENV_FILE}" <<'PYEOF'
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "ERROR: PyYAML missing. Install it (pip install pyyaml) or run "
        "this from the pipeline container.\n"
    )
    sys.exit(2)

compose_path, env_path = sys.argv[1], sys.argv[2]

with open(compose_path) as fh:
    compose = yaml.safe_load(fh)

services = compose.get("services", {}) or {}

# Build the set of hostnames Docker will resolve on the dataobs-poc
# network: every service name PLUS every declared network alias.
resolvable = set(services.keys())
for svc_name, svc in services.items():
    nets = svc.get("networks") or {}
    if isinstance(nets, dict):
        for net in nets.values():
            if isinstance(net, dict):
                for alias in net.get("aliases", []) or []:
                    resolvable.add(alias)

# Hosts that are explicitly external (real DNS / public APIs) and so
# don't have to be a compose service. Add to this list, don't relax
# the check for everything.
EXTERNAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"}

URL_PATTERN = re.compile(
    r"https?://([a-zA-Z0-9_.-]+)(?::\d+)?",
)
DOTEL_PATTERN = re.compile(
    r"-Dotel\.[\w.]*endpoint=https?://([a-zA-Z0-9_.-]+)(?::\d+)?",
)

problems: list[str] = []

def check_host(host: str, where: str) -> None:
    if host in EXTERNAL_HOSTS:
        return
    if host in resolvable:
        return
    if host.startswith("${") or "$" in host:
        # Variable substitution — out of scope for static check.
        return
    problems.append(f"{where}: host '{host}' is not a compose service name or alias")

def walk(value, path: str) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            walk(v, f"{path}[{i}]")
    elif isinstance(value, str):
        for host in URL_PATTERN.findall(value):
            check_host(host, path)
        for host in DOTEL_PATTERN.findall(value):
            check_host(host, path + "(SPARK_SUBMIT_OPTS)")

walk(services, "services")

# Check .env.poc OTEL endpoint values too.
env_problems: list[str] = []
if os.path.exists(env_path):
    with open(env_path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            for host in URL_PATTERN.findall(val):
                if host in EXTERNAL_HOSTS or host in resolvable:
                    continue
                env_problems.append(
                    f".env.poc:{lineno} {key}: host '{host}' is not a compose "
                    f"service name or alias"
                )
            for host in DOTEL_PATTERN.findall(val):
                if host in EXTERNAL_HOSTS or host in resolvable:
                    continue
                env_problems.append(
                    f".env.poc:{lineno} {key}: -Dotel...endpoint host "
                    f"'{host}' is not a compose service name or alias"
                )

print("Resolvable hosts on dataobs-poc network:")
for h in sorted(resolvable):
    print(f"  - {h}")
print()

if problems or env_problems:
    print("FAIL: unresolvable hosts found:")
    for p in problems + env_problems:
        print(f"  ✗ {p}")
    sys.exit(1)

print("OK: every URL host in docker-compose.poc.yml + .env.poc resolves "
      "to a compose service or declared alias.")
PYEOF
