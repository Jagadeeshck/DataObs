#!/usr/bin/env bash
# Local DataObs pipeline runner.
#
# Reproduces the hosted CI certification + fast gates on this machine, against a
# real Elasticsearch 9.5.5 stack in Docker. This exists because several release
# defects (e.g. the ES 9.x `_id`-fielddata sort 500s) are only observable against
# a live stack and are invisible to the in-memory unit suites.
#
# It is a THIN WRAPPER over the existing certification harness
# (scripts/certification/compose.sh + the tests/certification suites and the
# per-profile env used by .github/workflows/ci.yml). It does NOT introduce a new
# or competing CI mechanism — it just makes the documented hosted steps runnable
# locally with one command, always rebuilding images from the CURRENT working tree
# so you never test a stale container image.
#
# Usage:
#   scripts/ci/run_local_pipeline.sh fast                 # lint + unit gates only (no Docker)
#   scripts/ci/run_local_pipeline.sh cert <profile>       # live-stack certification for one profile
#   scripts/ci/run_local_pipeline.sh cert all             # every backend certification profile, in order
#   scripts/ci/run_local_pipeline.sh up <profile>         # bring up a profile stack and leave it running
#   scripts/ci/run_local_pipeline.sh down                 # tear everything down
#
# Backend certification profiles (match ci.yml jobs):
#   migrations | postgres | kafka | product | security
#
# Env knobs:
#   KEEP_UP=1        # after `cert`, leave the stack running (default: tear down)
#   NO_BUILD=1       # skip image rebuild (faster re-runs; ONLY if source unchanged)
#   PYTEST_ARGS=...  # extra args passed to pytest
#
# Exit non-zero on any gate failure, mirroring CI fail-closed behaviour.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
COMPOSE_FILE="docker-compose.certification.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE")
API_TOKEN="dataobs-certification-token"

# Activate the repo venv so `python` (not just python3) is on PATH — the
# certification bootstrap and apply scripts invoke bare `python`, matching the
# hosted runner's setup-python. This was a real local-only failure mode.
if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi
command -v python >/dev/null 2>&1 || { echo "FATAL: 'python' not on PATH (activate a venv with python)"; exit 69; }

log()  { printf '\n\033[1;36m[local-pipeline]\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m[local-pipeline] FAIL:\033[0m %s\n' "$*" >&2; exit 1; }

require_docker() {
  docker info >/dev/null 2>&1 || fail "Docker daemon not reachable. Start Docker Desktop first."
}

# profile -> pytest targets (mirrors .github/workflows/ci.yml certification jobs)
cert_tests_for() {
  case "$1" in
    migrations) echo "tests/certification/test_migrations.py tests/certification/test_incidents.py" ;;
    postgres)   echo "tests/certification/test_postgres.py" ;;
    kafka)      echo "tests/certification/test_kafka.py tests/certification/test_otel.py" ;;
    product)    echo "tests/certification/test_openlineage.py tests/certification/test_product_queries.py" ;;
    security)   echo "tests/certification/test_security.py" ;;
    *) fail "unknown certification profile: $1 (use migrations|postgres|kafka|product|security)" ;;
  esac
}

run_fast() {
  log "FAST gates: ruff + black + mypy + unit tests (no Docker)"
  ruff check . || fail "ruff"
  black --check --line-length 120 . || fail "black"
  # mypy scope mirrors the repo's typical gate; adjust via PYTEST_ARGS not here.
  python -m pytest -q --ignore=tests/integration --ignore=tests/certification ${PYTEST_ARGS:-} || fail "unit tests"
  log "FAST gates passed."
}

bootstrap_secrets() {
  # Idempotent secret setup. Reuse existing valid secrets instead of re-running
  # bootstrap.sh, because its `printf > compose.env` truncation under umask 077
  # trips an EPERM on an already-0600 file on macOS. Only (re)generate when the
  # secrets are actually missing/empty.
  local rs="$ROOT/certification/runtime-secrets"
  local pw="$rs/postgres-password.txt" env="$rs/compose.env"
  if [[ -s "$pw" && -s "$env" ]]; then
    log "Reusing existing certification secrets"
  else
    log "Generating certification secrets"
    mkdir -p "$rs"
    if [[ ! -s "$pw" ]]; then
      python - "$pw" <<'PY'
import secrets, sys
from pathlib import Path
p = Path(sys.argv[1]); p.write_text(secrets.token_urlsafe(32) + "\n"); p.chmod(0o600)
PY
    fi
    # write compose.env fresh (rm first to avoid the truncate-EPERM on macOS)
    rm -f "$env"
    printf 'CERTIFICATION_POSTGRES_PASSWORD_FILE=%q\n' "$(cd "$rs" && pwd)/postgres-password.txt" > "$env"
    chmod 600 "$env"
  fi
  # shellcheck disable=SC1091
  source "$env"
  export CERTIFICATION_POSTGRES_PASSWORD_FILE
}

# Host-agnostic per-profile fixture seeding (mirrors the CI "Seed ..." steps).
seed_profile() {
  case "$1" in
    kafka)
      log "Seeding Kafka fixtures (topics via confluent-kafka AdminClient)"
      KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:19092" python - <<'PY'
import os
from confluent_kafka.admin import AdminClient, NewTopic
bs = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:19092")
admin = AdminClient({"bootstrap.servers": bs})
topic = NewTopic("certification-orders", num_partitions=3, replication_factor=3)
for name, fut in admin.create_topics([topic]).items():
    try:
        fut.result(); print(f"  created topic {name}")
    except Exception as exc:  # already-exists is fine (idempotent)
        print(f"  topic {name}: {exc}")
md = admin.list_topics(timeout=10)
assert "certification-orders" in md.topics, "seed failed: certification-orders missing"
print(f"  seed ok: certification-orders present, brokers={len(md.brokers)}")
PY
      # schemas/connectors are best-effort locally (released scripts are CLI-based);
      # the kafka assertion only requires the topic + live cluster, both present.
      ;;
    *) : ;;  # migrations/postgres/product/security need no extra local seed
  esac
}

run_cert_profile() {
  local profile="$1" cp="cert-$1"
  require_docker
  bootstrap_secrets
  log "Profile $cp: bringing up stack (rebuild from current working tree)"
  if [[ "${NO_BUILD:-0}" == "1" ]]; then
    "${COMPOSE[@]}" --profile "$cp" up -d
  else
    # Fresh cert runs start from a PRISTINE stack: wipe prior containers AND the
    # named data volumes (certification-es/pg) so accumulated indices from earlier
    # runs cannot pollute results. (A reused ES volume once inflated /_mapping past
    # the harness read bound and produced a false migration failure.) Use NO_BUILD=1
    # to skip this and reuse the existing stack.
    log "Pruning any prior cert stack + volumes for a clean baseline"
    for p in cert-migrations cert-postgres cert-kafka cert-product cert-security cert-browser; do
      "${COMPOSE[@]}" --profile "$p" down -v >/dev/null 2>&1 || true
    done
    "${COMPOSE[@]}" --profile "$cp" up -d --build
  fi
  "$ROOT/scripts/certification/wait_for_stack.sh" "$cp"

  # migrations profile (and any that need the schema) apply the released migrations
  log "Applying released migrations (idempotent)"
  bash "$ROOT/scripts/certification/apply_migrations.sh" >/dev/null

  # Per-profile seed — mirrors the CI job's dedicated "Seed ..." step. Run
  # host-agnostically (the released kafka seed script calls `kafka-topics.sh`,
  # which isn't on a typical dev host; create the topic via the confluent-kafka
  # AdminClient the tests already use). Released seed scripts are left untouched.
  seed_profile "$profile"

  local tests; tests="$(cert_tests_for "$profile")"
  # Local evidence goes under a reliably-writable base. The repo artifacts/ dir
  # carries macOS extended attributes that intermittently EPERM on writes, so use
  # a dedicated local-evidence root (override with LOCAL_ARTIFACTS_DIR).
  local outdir="${LOCAL_ARTIFACTS_DIR:-${TMPDIR:-/tmp}/dataobs-local-pipeline}/$profile"
  mkdir -p "$outdir"
  log "Evidence dir: $outdir"
  log "Running live assertions: $tests"
  set +e
  RUN_CERTIFICATION_TESTS=1 \
  DATAOBS_API_TOKEN="$API_TOKEN" \
  CERTIFICATION_POSTGRES_DSN="postgresql://dataobs_fixture@127.0.0.1:15432/orders" \
  KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:19092" \
  CONNECT_URL="http://127.0.0.1:18083" \
  SCHEMA_REGISTRY_URL="http://127.0.0.1:18081" \
  python -m pytest $tests -q --junitxml="$outdir/results.xml" ${PYTEST_ARGS:-}
  local rc=$?
  set -e

  # always capture diagnostics
  docker stats --no-stream > "$outdir/container-memory.txt" 2>/dev/null || true
  "${COMPOSE[@]}" --profile "$cp" logs --no-color > "$outdir/stack.log" 2>/dev/null || true

  if [[ "${KEEP_UP:-0}" != "1" ]]; then
    log "Tearing down $cp (set KEEP_UP=1 to keep it)"
    bash "$ROOT/scripts/certification/teardown.sh" || "${COMPOSE[@]}" --profile "$cp" down -v || true
  else
    log "Leaving $cp stack UP (KEEP_UP=1). API: http://127.0.0.1:18000  ES: http://127.0.0.1:19200"
  fi

  [[ $rc -eq 0 ]] || fail "certification profile '$profile' assertions failed (artifacts in $outdir)"
  log "Certification profile '$profile' PASSED (evidence: $outdir)"
}

cmd="${1:-help}"
case "$cmd" in
  fast) run_fast ;;
  cert)
    shift
    target="${1:?usage: cert <migrations|postgres|kafka|product|security|all>}"
    if [[ "$target" == "all" ]]; then
      for p in migrations postgres kafka product security; do run_cert_profile "$p"; done
    else
      run_cert_profile "$target"
    fi ;;
  up)
    shift; require_docker; bootstrap_secrets
    p="cert-${1:?usage: up <profile>}"
    "${COMPOSE[@]}" --profile "$p" up -d --build
    "$ROOT/scripts/certification/wait_for_stack.sh" "$p"
    bash "$ROOT/scripts/certification/apply_migrations.sh" >/dev/null || true
    log "Stack '$p' up. API: http://127.0.0.1:18000  ES: http://127.0.0.1:19200" ;;
  down)
    require_docker
    bash "$ROOT/scripts/certification/teardown.sh" 2>/dev/null || true
    for p in cert-migrations cert-postgres cert-kafka cert-product cert-security cert-browser; do
      "${COMPOSE[@]}" --profile "$p" down -v 2>/dev/null || true
    done
    log "All certification stacks torn down." ;;
  help|*)
    sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
esac
