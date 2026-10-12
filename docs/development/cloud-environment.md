# Cloud development environment

Use this workflow to develop and validate the Python API and React console in an
isolated cloud task. It runs the API with an in-memory store and uses the existing
console proxy. Elasticsearch, Docker, and integration credentials are unnecessary
for this local workflow. Live integration and hosted certification checks require
their separately documented services and configuration.

Each cloud task already has an isolated checkout. Use that checkout; do not create
a Git worktree unless the user explicitly requests one.

## Install

The validated cloud runtime provides Python 3.12 and Node.js 24 with npm. The console
pins pnpm 10.28.1 in its package manifest. Dependency installation needs access to
PyPI and the npm registry.

Run from the checkout root:

```bash
cd /workspace/DataObs
export DATAOBS_TOOLS_DIR="${DATAOBS_TOOLS_DIR:-/workspace/.dataobs-tools}"
bash scripts/cloud/setup.sh
source "$DATAOBS_TOOLS_DIR/venv/bin/activate"
```

The [setup script](../../scripts/cloud/setup.sh) installs the runtime and CI Python
requirements, checks their compatibility, installs pnpm 10.28.1, installs console
dependencies with the committed frozen lockfile, and builds the console. It
calculates the checkout root from its own location, so the checkout can live at
another path.

`DATAOBS_TOOLS_DIR` can point to another writable absolute path **outside the
checkout**. It holds the virtual environment, pnpm executable, and dependency
caches. Keeping Python dependencies outside the repository avoids third-party
source files being included in repository-wide scanning tests. Activate the
virtual environment before running backend tests so their Python subprocesses
also use the installed dependencies.

Installation prepares dependencies and build output. Running processes are not
preserved in an environment snapshot; start the services in each task that needs
them.

## Start the API and console

In the API terminal, activate the environment and run the API in the foreground:

```bash
cd /workspace/DataObs
export DATAOBS_TOOLS_DIR="${DATAOBS_TOOLS_DIR:-/workspace/.dataobs-tools}"
source "$DATAOBS_TOOLS_DIR/venv/bin/activate"
DATAOBS_STORE_BACKEND=memory \
DATAOBS_ALLOW_UNAUTHENTICATED_DEV=true \
API_HOST=127.0.0.1 API_PORT=8000 \
python -m src.api.main
```

This configuration enables local development without a token when authentication
credentials are absent. Existing authentication bindings still apply if supplied
by the environment. The development setting is intended for an isolated local
workflow. The memory store starts empty and loses its data when the API process
stops.

In a separate console terminal:

```bash
cd /workspace/DataObs/ui/dataobs-console
export DATAOBS_TOOLS_DIR="${DATAOBS_TOOLS_DIR:-/workspace/.dataobs-tools}"
"$DATAOBS_TOOLS_DIR/node_modules/.bin/pnpm" dev \
  --host 127.0.0.1 --port 5173 --strictPort
```

The console's existing Vite configuration proxies `/api` requests to the API on
port 8000. Keep the API on that port for this workflow. `--strictPort` makes a
console port conflict explicit. Keep both processes running in their managed
terminals and stop them with Ctrl+C when finished.

## Check the running services

In a third terminal, check API health, local readiness, the console response, and
a console request that reaches the API:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/readyz
curl -fsS http://127.0.0.1:5173/ -o /dev/null
curl -fsS http://127.0.0.1:5173/api/v1/auth/config
```

Readiness should report `local-memory-mode`. With the default unauthenticated
development configuration, exercise rule creation, listing, and deletion:

```bash
curl -fsS --json \
  '{"rule_id":"cloud-dev-smoke","dataset":"cloud.dev.orders","check_type":"freshness","severity":"medium"}' \
  http://127.0.0.1:8000/rules
curl -fsS 'http://127.0.0.1:8000/rules?dataset=cloud.dev.orders'
curl -fsS -X DELETE http://127.0.0.1:8000/rules/cloud-dev-smoke
```

If the environment supplies authentication credentials, use the existing
authorized authentication flow for protected requests. Keep secret values in
environment settings rather than repository files or shell history.

## Validate changes

Run the backend suite that does not require live integration services:

```bash
cd /workspace/DataObs
export DATAOBS_TOOLS_DIR="${DATAOBS_TOOLS_DIR:-/workspace/.dataobs-tools}"
source "$DATAOBS_TOOLS_DIR/venv/bin/activate"
python -m pytest tests --ignore=tests/integration -q
```

Run the console tests, type check, build, and bundle and performance budgets:

```bash
cd /workspace/DataObs/ui/dataobs-console
export DATAOBS_TOOLS_DIR="${DATAOBS_TOOLS_DIR:-/workspace/.dataobs-tools}"
"$DATAOBS_TOOLS_DIR/node_modules/.bin/pnpm" test
"$DATAOBS_TOOLS_DIR/node_modules/.bin/pnpm" typecheck
"$DATAOBS_TOOLS_DIR/node_modules/.bin/pnpm" build
"$DATAOBS_TOOLS_DIR/node_modules/.bin/pnpm" bundle:check
"$DATAOBS_TOOLS_DIR/node_modules/.bin/pnpm" performance:check
```

These are the local validation checks for this environment. Some backend tests
can skip when optional SDKs are absent; inspect the pytest summary. Successful
local checks do not establish live integration or hosted certification readiness.
Consult [CI validation](ci-validation.md) and the relevant integration or
certification instructions when a change needs those checks.

Setup should leave tracked source files, dependency declarations, lockfiles, and
generated API schemas unchanged. Do not run schema generation as an installation
step. Review `git status --short` after setup to distinguish expected ignored
dependencies and build output from unintended changes.
