# Running the DataObs pipeline locally

Several release defects are only observable against a **real Elasticsearch 9.5.5
stack** and are invisible to the in-memory unit suites — for example the ES 9.x
`_id`-fielddata sort 500s (B15/B16). Going forward, run the certification pipeline
locally before relying on a change, using the documented runner.

## Entry point

```
scripts/ci/run_local_pipeline.sh <command>
```

It is a thin wrapper over the existing certification harness
(`scripts/certification/compose.sh`, the `tests/certification/*` suites, and the
per-profile env from `.github/workflows/ci.yml`). It does **not** add a competing
CI mechanism — it makes the hosted steps runnable locally and **always rebuilds
images from the current working tree** so you never test a stale container.

## Commands

| Command | What it does |
|---|---|
| `run_local_pipeline.sh fast` | Lint + unit gates only (ruff, black, mypy, unit pytest). No Docker. |
| `run_local_pipeline.sh cert <profile>` | Live-stack certification for one profile. |
| `run_local_pipeline.sh cert all` | All backend profiles in order: migrations, postgres, kafka, product, security. |
| `run_local_pipeline.sh up <profile>` | Bring a profile stack up and leave it running (for manual curl/debug). |
| `run_local_pipeline.sh down` | Tear every certification stack down (`-v`). |

Backend profiles mirror the `ci.yml` certification jobs:
`migrations | postgres | kafka | product | security`
(each maps to the same `tests/certification/test_*.py` the hosted job runs).

## Env knobs

- `KEEP_UP=1` — after `cert`, leave the stack running (default: tear down).
- `NO_BUILD=1` — skip the image rebuild. **Only** when source is unchanged; a stale
  image silently tests old code (this bit us once — incidents showed 500 after a
  merge because the container still had pre-fix code).
- `PYTEST_ARGS=...` — extra args passed to pytest.

## Prerequisites (one-time)

- Docker Desktop running (`docker info` must succeed). Give it ≥ 8 GB RAM.
- `kind` + `helm` installed (for the Kubernetes/Helm deployment gate): `brew install kind helm`.
- The repo venv at `.venv` (the runner activates it so bare `python`, which the
  harness scripts call, is on PATH).

## Trustworthy runs

- Prefer a **fresh** run (omit `NO_BUILD`) so the stack is pristine and the image
  matches the current tree. A long-lived, mutated ES instance can accumulate state
  (e.g. indices recreated by opt-in integration tests) that produces misleading
  assertion failures unrelated to your change.
- Do **not** run opt-in real-ES integration tests against a cert stack you intend to
  keep — they recreate indices and can break the migration baseline. Use a fresh
  profile bring-up instead.

## Ports (when a stack is up)

- Elasticsearch: `http://127.0.0.1:19200`
- API: `http://127.0.0.1:18000`  (auth: `Authorization: Bearer dataobs-certification-token`,
  headers `X-DataObs-Tenant: tenant-alpha`, `X-DataObs-Environment: staging`)
- Kibana/Console (browser profile): `http://127.0.0.1:18080`
- Kafka Connect / Schema Registry (kafka profile): `18083` / `18081`

## Typical loop while fixing a live-only defect

```
scripts/ci/run_local_pipeline.sh up migrations      # pristine stack
# ... make the fix ...
docker compose -f docker-compose.certification.yml --profile cert-migrations up -d --build api
curl -s -o /dev/null -w '%{http_code}\n' \
  -H 'Authorization: Bearer dataobs-certification-token' \
  -H 'X-DataObs-Tenant: tenant-alpha' -H 'X-DataObs-Environment: staging' \
  http://127.0.0.1:18000/api/v1/<endpoint>            # expect 200, not 500
scripts/ci/run_local_pipeline.sh cert migrations     # full profile assertions
scripts/ci/run_local_pipeline.sh down                # when done
```
