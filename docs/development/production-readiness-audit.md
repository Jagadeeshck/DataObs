# Production Readiness Audit

**Repository:** `Jagadeeshck/DataObs`  
**Audit date:** 2026-05-15  
**Scope reviewed:** `src/`, `tests/`, `config/`, root and integration Docker Compose files, Dockerfiles, Helm chart, Terraform modules, GitHub Actions, docs, integrations, tools, POC code, and Kubernetes manifests.

## Executive summary

DataObs is a strong observability platform starter: it includes a runnable API, a quality engine, Elasticsearch-backed persistence, OpenTelemetry collector configs, alerting clients, Helm/Kubernetes manifests, Terraform modules, and broad unit test coverage. The repository is not yet fully production-ready as a product runtime because several production paths still rely on local-dev defaults, ad-hoc configuration, and POC-oriented deployment assumptions.

The most important production-readiness work should be incremental, not a rewrite:

1. **Establish explicit runtime boundaries.** Keep `src/api`, `src/quality`, `src/analytics`, `src/alerting`, `src/core`, and `src/telemetry.py` as production runtime modules; keep `src/poc`, `Dockerfile.poc`, `.env.poc`, `config/dataobs_poc.yaml`, `config/poc_defaults.yaml`, `docker-compose.poc.yml`, `kibana/`, and POC setup docs clearly marked as demo/POC assets.
2. **Harden the API and persistence path.** `src/api/main.py` currently uses `http.server`, module globals, optional authentication, and mixed store wiring. `src/api/store.py` defaults to in-memory storage, while `src/api/es_store.py` provides tenant-aware Elasticsearch storage. This is acceptable for a starter, but production should default to durable storage, explicit tenancy, request validation, pagination, readiness checks, structured errors, and a real ASGI/WSGI framework.
3. **Make deployment artifacts production-safe by default.** Docker images run as non-root, but Helm/Kubernetes lack secrets, probes, pod security contexts, network policies, autoscaling, and pinned release images. Terraform modules are useful but need stronger bootstrap/migration guidance, least-privilege tightening after first apply, and CI validation across all modules.
4. **Improve CI/CD confidence.** CI runs tests, config validation, Docker builds, Trivy on the sample app image, Terraform plan for one root module, and dbt tests. It should add static type/lint/security checks, Helm rendering/linting, image scans for production images, compose smoke tests, and integration test gates.
5. **Document production operations and migration steps.** Existing docs explain architecture and production deployment, but they need an operator-focused runbook for secrets, tenant onboarding, schema/index migrations, API contracts, SLOs, backup/restore, rollback, and POC-to-production promotion boundaries.

## Test results during audit

| Command | Result | Notes |
| --- | --- | --- |
| `python --version` | Passed | Runtime was Python `3.14.4`, while images and CI target Python 3.11. |
| `python -m pytest -q` | Passed | `242 passed, 5 skipped, 1 warning in 9.10s`. Skips were service-backed integration tests gated by `RUN_INTEGRATION_TESTS=1`. Warning: `src/poc/apm.py:230` has `return` in a `finally` block. |

## Asset classification

### 1. Production runtime code

These modules should be treated as shippable runtime code and protected with production API, persistence, compatibility, and security standards:

- `src/api/main.py` — HTTP API server for health, rules, lineage, quality results, and enterprise backlog.
- `src/api/store.py` and `src/api/es_store.py` — in-memory, legacy Elasticsearch, and tenant-aware Elasticsearch store implementations.
- `src/quality/engine.py` — APScheduler-based quality check runner, Elasticsearch writer, and OTel emitter.
- `src/quality/checks/*.py`, `src/quality/freshness.py`, `src/quality/lineage.py`, `src/quality/baseline_store.py` — data quality, freshness, drift, lineage, and baseline logic.
- `src/analytics/anomaly_detector.py` and `src/analytics/elasticsearch_ml.py` — anomaly and Elasticsearch ML support.
- `src/alerting/slack.py`, `src/alerting/pagerduty.py`, `src/alerting/servicenow.py` — outbound incident/notification integrations.
- `src/core/enterprise_blueprint.py`, `src/core/pillars.py`, and `src/telemetry.py` — product taxonomy and telemetry helpers.
- `Dockerfile.api`, `Dockerfile.quality`, `docker-compose.yml`, `k8s/*.yaml`, and `helm/dataobs/**` — production-ish packaging and deployment entry points.
- `config/dataobs.example.yaml`, `config/otel-collector-config.yaml`, `config/otel-ec2-agent-config.yaml`, `config/aws/**`, `config/elasticsearch/**`, and `config/opensearch/**` — production configuration templates and backend bootstrap assets.
- `infra/terraform/**` — infrastructure provisioning for AWS, OpenSearch/Elasticsearch, AMP, AMG, OSIS, IAM, and EC2 OTel agents.
- `.github/workflows/ci.yml` and `.github/workflows/release.yml` — CI and release automation.

### 2. POC/demo code

These assets should remain easy to run but isolated from production contracts:

- `src/poc/**` — POC ETL, Spark, Kibana bootstrap, POC telemetry, Elastic APM helpers, and synthetic datasets.
- `Dockerfile.poc`, `requirements-poc.txt`, `.env.poc`, `docker-compose.poc.yml`, `scripts/run_poc_pipeline.sh`, `scripts/verify_poc.sh`, `scripts/validate_poc_compose.sh`, and `scripts/validate_otel_config.py`.
- `config/dataobs_poc.yaml`, `config/poc_defaults.yaml`, `config/otel-collector-poc.yaml`, and `kibana/dataobs-poc-saved-objects.ndjson`.
- `docs/poc-setup.md` and `docs/poc-elastic-agent-observability.md`.

### 3. Integrations

These are connector/example packages that should have their own compatibility matrices and release expectations:

- `integrations/aws-lambda/layer/otel_lambda.py`, `integrations/aws-lambda/examples/s3_event_processor.py`, and `integrations/aws-lambda/README.md`.
- `integrations/dbt/parse_run_results.py`, `integrations/dbt/dbt_cloud_poller.py`, `integrations/dbt/requirements.txt`, and `tests/test_dbt_integration.py`.
- `integrations/spark/otel_spark.py`, `integrations/spark/example_etl_job.py`, `integrations/spark/example_streaming.py`, `integrations/spark/config/otel-collector-spark.yaml`, and `tests/test_spark_instrumentation*.py`.
- `integrations/grafana-alloy/**`, including the sample app, Alloy config, compose file, dashboards, and guide.
- `tools/alloy-config-gen/**` — tenant config generation helper.

### 4. Docs/examples

These should be reviewed for accuracy and drift, but are not runtime code:

- `README.md`, `CONTRIBUTING.md`, `docs/api/rules-and-lineage-api.md`, `docs/architecture/**`, `docs/product/**`, `docs/production/**`, `docs/towers/**`, `docs/wiki/**`, `k8s/README.md`, `helm/dataobs/README.md`, and integration READMEs.

## Findings by area

### API architecture

**Current state**

- `src/api/main.py` uses Python `http.server.ThreadingHTTPServer` and a custom `BaseHTTPRequestHandler`.
- Authentication is a single shared bearer token via `API_TOKEN`; if the variable is unset, all non-health endpoints are allowed.
- Store instances are module-level globals (`_store`, `_rule_store`, `_lineage_store`) initialized in `main()`.
- JSON body parsing does not enforce a maximum size, content type, schema, or required fields.
- List endpoints do not expose pagination, filtering, sorting, or query parameter validation even though store methods support some filters.
- `/health` confirms the process is running but does not validate Elasticsearch connectivity or downstream dependencies.

**Risks**

- Optional authentication is dangerous if `Dockerfile.api`, Helm, or Compose are deployed without `API_TOKEN`.
- The shared-token model has no tenant/user identity, no token rotation story, no authorization model, and weak auditability.
- `http.server` lacks the middleware ecosystem, request lifecycle hooks, OpenAPI generation, rate limiting, and standard error handling expected for a production API.
- Globals make test setup simple, but they complicate dependency injection, graceful shutdown, background resources, and multi-tenant request scoping.

**Quick wins**

- Fail startup in production mode when `API_TOKEN` or stronger auth config is missing.
- Add request body size limits, `Content-Type: application/json` enforcement, schema validation, and consistent `{error, code, details}` responses.
- Split `/health` into liveness and readiness endpoints, with readiness checking Elasticsearch when `DATAOBS_STORE_BACKEND=elasticsearch`.
- Add basic pagination/query parameters for `/rules`, `/quality/results`, `/lineage/nodes`, and `/lineage/edges`.

**Deeper refactors**

- Migrate the API incrementally to FastAPI or another ASGI framework while preserving route compatibility. Start by wrapping the existing store interfaces, then generate OpenAPI and move one route group at a time.
- Introduce an application factory that accepts config, logger, store, auth provider, and telemetry dependencies.
- Add tenant-aware request context and authorization checks before adding customer-facing multi-tenancy.

### Persistence and data model

**Current state**

- `src/api/store.py` defaults to `InMemoryStore` unless `DATAOBS_STORE_BACKEND=elasticsearch` is set.
- `src/api/es_store.py` provides a tenant-aware Elasticsearch store with ILM policy creation and indices for quality, rules, and lineage.
- `src/api/store.py` also keeps older `RuleStore` and `LineageStore` classes using fixed indices (`dataobs-rules`, `dataobs-lineage-nodes`, `dataobs-lineage-edges`).
- `src/api/main.py` initializes both unified and legacy stores, then routes some calls through `_store`, `_rule_store`, or `_lineage_store`.
- `src/quality/lineage.py` writes lineage graph documents directly to Elasticsearch indices that must stay aligned with API store constants.
- `config/elasticsearch/server/*.json`, `config/elasticsearch/tenant/*.yaml`, and bootstrap scripts provide index templates, ILM, ingest pipelines, and tenant overlays, but those assets are not clearly wired into runtime migrations.

**Risks**

- In-memory default can silently lose data in a production-like deployment.
- Dual store models create schema drift risk between unified tenant-aware indices and legacy fixed-index lineage/rule paths.
- Index creation during runtime can surprise operators; production should use explicit migrations/bootstrap jobs with reviewed mappings.
- Store methods catch broad exceptions and often return empty lists/`None`, which may hide production incidents.

**Quick wins**

- Change docs and deployment values so durable Elasticsearch is the default for production examples, with memory explicitly marked local-only.
- Add a `DATAOBS_ENV=production` guard that rejects `DATAOBS_STORE_BACKEND=memory`.
- Add structured logging and metrics for store errors instead of returning empty data silently.
- Add a schema/version document per index prefix to make bootstrap idempotency auditable.

**Deeper refactors**

- Define a single store protocol and migrate API, quality, and lineage code to it.
- Move index creation and ILM/template setup to explicit bootstrap/migration commands, then run them as CI-validated artifacts or Kubernetes Jobs.
- Add optimistic concurrency or version fields for mutable rules and lineage nodes.

### Configuration management

**Current state**

- Runtime configuration is split across environment variables, `config/dataobs.example.yaml`, `config/dataobs_poc.yaml`, `config/poc_defaults.yaml`, Helm values, Docker Compose variables, and Terraform variables.
- `src/quality/engine.py` loads YAML from `DATAOBS_CONFIG`, while `src/api/main.py` primarily reads environment variables.
- `helm/dataobs/values.yaml` embeds Elasticsearch credentials fields and collector config in a ConfigMap-style value block, with comments warning not to commit real passwords.
- `.env.example` and `.env.poc` serve different local/demo paths.

**Risks**

- Different services may interpret config differently, leading to drift between API, quality engine, and collector deployments.
- Secrets can accidentally land in ConfigMaps or checked-in values files.
- There is no typed configuration model or validation step for the full production config.

**Quick wins**

- Add a single typed config loader module and use it from both API and quality engine.
- Document precedence rules: CLI/env vars, Kubernetes Secret, ConfigMap/YAML, defaults.
- Add CI validation for `config/dataobs.example.yaml`, `helm/dataobs/values.yaml`, and production docs snippets.
- Move Helm secret fields to `existingSecret` references and keep non-secret config in ConfigMaps.

**Deeper refactors**

- Introduce versioned configuration schemas and migration notes.
- Support secret references from AWS Secrets Manager, Kubernetes Secrets, and environment variables without embedding secret values in YAML.

### Observability

**Current state**

- `src/quality/engine.py` initializes OTel traces and metrics and emits quality check counters.
- Collector configs exist for root production/local, POC, EC2 agent, Spark, Grafana Alloy, AWS/OpenSearch, and tenant overlays.
- `src/api/main.py` does not initialize OTel tracing/metrics for HTTP requests.
- Docker and Kubernetes provide health checks in some places, but deployment manifests do not consistently expose liveness/readiness probes or collector self-metrics scraping.

**Risks**

- The API itself may become a blind spot during incidents.
- Lack of standard resource attributes and service version tags makes release correlation difficult.
- Collector pipeline health is documented, but not enforced through Helm defaults or automated smoke tests.

**Quick wins**

- Add API request logs with request ID, route, status, duration, tenant, and trace IDs.
- Add API OTel instrumentation and RED metrics.
- Add Helm probes and optional `ServiceMonitor`/scrape annotations for API, quality, and collector self-metrics.
- Add dashboards/alerts for API error rate, latency, Elasticsearch write failures, quality job failures, and collector refused/dropped telemetry.

**Deeper refactors**

- Standardize semantic conventions across API, quality, Spark, Lambda, dbt, and POC assets.
- Add end-to-end trace correlation from data quality result to API read path to alert delivery.

### Security

**Current state**

- Docker production images create and use a non-root `dataobs` user.
- Alerting clients redact secret-like values in `__repr__` and tests cover some integrations.
- `src/quality/checks/sql.py` validates identifiers before interpolating SQL identifiers into quality queries.
- Terraform modules include encryption, TLS, IAM, KMS, S3 public access blocks, and OpenSearch fine-grained access control in several areas.
- CI scans only the sample app image for critical/high CVEs; production images are built but not scanned in the visible CI path.

**Risks**

- API auth is optional by default and uses a single static secret.
- Helm/Kubernetes manifests do not define pod/container security contexts, read-only root filesystems, network policies, service accounts, or secret references.
- Terraform bootstrap notes allow broad OSIS pipeline ARN permissions (`*`) until tightened after first apply; this needs an enforced follow-up control.
- Dependency pins are broad ranges and there is no lockfile, SBOM check gate, `pip-audit`, or secret scanning workflow.

**Quick wins**

- Require auth in production and document local-only unauthenticated mode.
- Scan `Dockerfile.api` and `Dockerfile.quality` images with Trivy in CI, not only the sample app.
- Add `pip-audit` or equivalent dependency vulnerability scanning.
- Add GitHub secret scanning guidance and pre-commit hooks for docs/config examples.
- Add Kubernetes `securityContext`, `runAsNonRoot`, `readOnlyRootFilesystem`, dropped capabilities, and network policy templates.

**Deeper refactors**

- Replace shared bearer token with OIDC/JWT validation or an API gateway integration.
- Add RBAC and tenant-aware authorization.
- Add audit logs for rule changes, lineage writes, quality result mutations, and alert delivery actions.

### CI/CD and release engineering

**Current state**

- `.github/workflows/ci.yml` validates selected configs, runs tests, builds API/quality/sample images, scans the sample app image, runs Terraform plan for `infra/terraform/aws-backend`, and runs dbt integration tests.
- `.github/workflows/release.yml` builds/pushes three images to GHCR on semver tags and publishes a GitHub release with SBOM/provenance enabled through Docker buildx.
- `pyproject.toml` contains pytest configuration but no package metadata, linting, formatting, typing, or coverage configuration.

**Risks**

- CI does not appear to lint or type-check core runtime modules.
- Helm templates are not rendered or linted in CI.
- Terraform validation is focused on `infra/terraform/aws-backend`, while other modules/root directories can drift.
- Integration tests are skipped by default locally and in the general unit test run.
- Release images use `latest` in Helm defaults, which is not reproducible for production rollouts.

**Quick wins**

- Add `ruff`, `mypy` or `pyright`, `bandit`, `pip-audit`, and coverage thresholds in CI.
- Add `helm lint` and `helm template` checks.
- Add Trivy scans for API and quality images.
- Add Docker Compose config checks for `docker-compose.poc.yml` and service-backed integration smoke tests behind a nightly or manual workflow.
- Pin Helm values examples to versioned image tags rather than `latest` for production guidance.

**Deeper refactors**

- Package the Python runtime as an installable project with explicit optional extras: `api`, `quality`, `poc`, `spark`, `dbt`, `lambda`.
- Add release promotion stages: build, scan, integration environment, signed release, Helm chart package, rollout verification.

### Packaging and dependency management

**Current state**

- Dependencies live in `requirements.txt`, `requirements-poc.txt`, and integration-specific requirements files.
- Dockerfiles install dependencies directly from requirements files and copy source into images.
- There is no lockfile, generated SBOM check, or published Python package metadata.

**Risks**

- Broad dependency ranges may produce different behavior across local, CI, and production builds.
- POC dependencies can be heavier and riskier if accidentally mixed with runtime images.
- Python 3.14 local test success is encouraging, but production images and CI use Python 3.11; compatibility claims should be explicit.

**Quick wins**

- Split dependency groups and add lock/constraints files for runtime images.
- Add an image label for Git SHA/version and set `OTEL_RESOURCE_ATTRIBUTES`/service version during image build or deployment.
- Ensure POC-only dependencies never enter API/quality images.

**Deeper refactors**

- Move to `pyproject.toml` packaging with extras and deterministic builds.
- Publish signed container images and a packaged Helm chart per release.

### Testing

**Current state**

- Unit tests are broad: API endpoints/store, Elasticsearch store behavior, quality checks, lineage, alerting clients, ServiceNow, POC ETL/pipeline, Spark instrumentation, dbt integration, and Elasticsearch ML.
- Service-backed integration tests under `tests/integration/**` are skipped unless `RUN_INTEGRATION_TESTS=1`.
- CI excludes service-backed integration tests from the main Python test job.

**Risks**

- Passing unit tests may not catch Elasticsearch, collector, Docker Compose, Helm, and Terraform integration failures.
- No visible coverage gate or mutation/contract tests for API compatibility.
- Tests cover POC code significantly, but production runtime hardening needs more negative-path and failure-mode coverage.

**Quick wins**

- Add API contract tests from an OpenAPI spec once the API framework migration begins.
- Add integration tests for Elasticsearch bootstrap, index templates, ILM, store CRUD, and alert retry/failure behavior.
- Add tests for config validation and production-mode startup guards.
- Add a nightly Docker Compose smoke test using `tests/integration/docker-compose.test.yml`.

**Deeper refactors**

- Build an ephemeral integration environment in CI with Elasticsearch/OpenSearch and OTel Collector.
- Add chaos/failure tests for ES unavailable, collector unavailable, invalid credentials, alerting endpoint timeouts, and schema migration failures.

### Deployment: Docker, Compose, Kubernetes, Helm

**Current state**

- `Dockerfile.api` and `Dockerfile.quality` use multi-stage builds and non-root users.
- `Dockerfile.poc` includes Java/PySpark and is intentionally demo-heavy.
- `docker-compose.yml` offers local full-stack backends and profiles; `docker-compose.poc.yml` is demo-specific.
- `k8s/*.yaml` and `helm/dataobs/**` deploy API, quality, and collector components.

**Risks**

- Helm defaults use `latest` image tags and empty resource blocks.
- Deployment templates lack readiness/liveness probes, security contexts, service account controls, pod disruption budgets, autoscaling, network policies, and Secret references.
- Collector credentials in Helm values rely on environment placeholders, but the Deployment does not clearly mount/populate `ELASTIC_USER`, `ELASTIC_PASSWORD`, or `ELASTIC_ENDPOINT` from Secrets.
- Raw `k8s/` manifests can drift from Helm templates.

**Quick wins**

- Add probes, resource requests/limits, pod/container security contexts, service accounts, and Secret wiring to Helm.
- Mark raw `k8s/` as generated/reference or add a sync process from Helm templates.
- Add production values examples for external Elasticsearch, external OTel, and locked image tags.

**Deeper refactors**

- Add Helm chart tests and progressive delivery guidance.
- Add migrations/bootstrap as Kubernetes Jobs with clear ordering before API/quality rollout.

### Terraform and cloud infrastructure

**Current state**

- `infra/terraform/aws-backend` composes AMP, IAM, OSIS, AMG, and dashboard modules.
- `infra/terraform/elasticsearch/server` and `infra/terraform/elasticsearch/tenant` support OpenSearch/Elasticsearch-oriented provisioning and tenant setup.
- `infra/terraform/aws-ec2-otel-agent` deploys/configures OTel agents through SSM associations.
- Modules include useful outputs, variables, README files, dashboards, KMS, logging, and encryption controls.

**Risks**

- `aws-backend` notes a first-apply broad IAM placeholder for OSIS pipeline ARN; without a tracked follow-up, least privilege can remain incomplete.
- Terraform CI validates only one root module and depends on change detection.
- Some resources use time-based values (for example maintenance schedules using `timestamp()` patterns) that can create plan churn if not carefully handled.
- Multi-account, state backend, drift detection, import, and destroy protection guidance is limited.

**Quick wins**

- Add `terraform validate`/`fmt` for all root modules and reusable modules.
- Add tfsec/checkov/tflint in CI.
- Add a post-bootstrap checklist or automated second apply to replace wildcard OSIS permissions with concrete ARNs.
- Document state backend, workspace/account strategy, import flow, and rollback.

**Deeper refactors**

- Create environment overlays for dev/staging/prod instead of relying on variable examples.
- Add Terraform tests or Terratest-style smoke checks for key module outputs and security assertions.

### Documentation

**Current state**

- The repository has strong architecture, production, integration, and POC docs.
- `docs/development/repository-structure.md`, `docs/production/production-guide.md`, `docs/api/rules-and-lineage-api.md`, and integration docs are good starting points.

**Risks**

- README calls the repository production-ready, but several runtime defaults and deployment artifacts are still starter/blueprint quality.
- POC/demo assets and production runtime assets are close together, increasing the chance that users deploy demo defaults.
- Operator runbooks are incomplete for migrations, alert routing, tenant onboarding, backup/restore, incident response, and release rollback.

**Quick wins**

- Update docs to explicitly say which commands are local-only, POC-only, or production-supported.
- Add a production readiness checklist linked from README and `docs/production/production-guide.md`.
- Add runbooks for API auth rotation, ES index bootstrap/migration, tenant onboarding, alert delivery testing, and restore drills.

**Deeper refactors**

- Maintain versioned docs tied to releases.
- Generate API docs from OpenAPI and validate examples in CI.

## Prioritized roadmap

### P0 — Production safety gates before any production deployment

1. **Require durable storage in production.** Add a startup guard so `DATAOBS_ENV=production` cannot run with `DATAOBS_STORE_BACKEND=memory`; update Helm/production docs to use Elasticsearch explicitly.
2. **Require API authentication in production.** Fail startup when production mode lacks API auth, and document local-only unauthenticated mode.
3. **Add Kubernetes secret wiring and remove secret-shaped values from ConfigMaps.** Helm should use `existingSecret`/`secretKeyRef` for API token and Elasticsearch credentials.
4. **Add readiness/liveness probes.** API readiness should check the selected store; collector readiness should use its health extension; quality engine should expose or otherwise report scheduler health.
5. **Scan production images.** Extend Trivy scans to `Dockerfile.api` and `Dockerfile.quality` images.
6. **Add production-mode config validation.** Validate required Elasticsearch, OTel, tenant, auth, and alerting settings before service start.
7. **Document POC boundaries.** Add clear labels in README/docs that `src/poc`, `Dockerfile.poc`, `.env.poc`, `docker-compose.poc.yml`, and `config/dataobs_poc.yaml` are non-production.
8. **Track Terraform least-privilege tightening.** Ensure wildcard OSIS pipeline IAM bootstrap is replaced after first apply.

### P1 — Stabilize contracts and operations

1. **Introduce a typed config module.** Use it in API and quality engine, with documented precedence and schema validation.
2. **Unify store interfaces.** Define one protocol for rules, quality results, and lineage; migrate legacy `RuleStore`/`LineageStore` calls behind it.
3. **Add API request validation and pagination.** Validate JSON schemas, content types, query parameters, and maximum request sizes.
4. **Add API observability.** Emit request metrics, traces, structured logs, request IDs, tenant IDs, and store error metrics.
5. **Add Helm lint/template CI and Terraform validation for all modules.** Include `helm lint`, `helm template`, `terraform fmt -check -recursive`, `terraform validate`, and tflint/checkov or equivalents.
6. **Add integration test workflow.** Run service-backed API + Elasticsearch + collector smoke tests on a schedule or manual dispatch.
7. **Add dependency and static analysis gates.** Add `ruff`, type checking, `bandit`, `pip-audit`, and coverage reporting.
8. **Create operational runbooks.** Cover tenant onboarding, index bootstrap/migration, backup/restore, alert testing, API token rotation, and rollback.

### P2 — Product-grade platform maturity

1. **Migrate API to ASGI with OpenAPI.** Preserve existing routes while incrementally moving route groups to FastAPI or equivalent.
2. **Add OIDC/JWT/RBAC.** Replace shared token auth with identity-aware, tenant-aware authorization.
3. **Move index setup to versioned migrations.** Use explicit bootstrap/migration commands or jobs rather than runtime index creation.
4. **Package Python modules with extras and lockfiles.** Separate `api`, `quality`, `integrations`, and `poc` dependencies.
5. **Publish versioned Helm charts.** Release chart artifacts alongside signed images and SBOM/provenance.
6. **Add SLO dashboards and alert packs.** Include default production alerts for API, quality scheduler, collector pipeline, ES/OpenSearch, and alert delivery.
7. **Add multi-environment Terraform overlays.** Support dev/staging/prod with repeatable state, account, and variable patterns.
8. **Add failure-mode tests.** Cover ES outages, credential failures, collector backpressure, alert endpoint timeouts, schema migration failures, and tenant isolation.

## Recommended GitHub issues to create or update

### P0 issues

1. **P0: Enforce production startup guards for auth and durable storage**
   - Files: `src/api/main.py`, `src/api/store.py`, `src/quality/engine.py`, `config/dataobs.example.yaml`, `docs/production/production-guide.md`, `helm/dataobs/values.yaml`.
   - Acceptance: production mode fails fast without auth; memory store is blocked in production; tests cover production and local-dev modes.

2. **P0: Move Helm secrets to Kubernetes Secret references**
   - Files: `helm/dataobs/values.yaml`, `helm/dataobs/templates/deployment-api.yaml`, `helm/dataobs/templates/deployment-quality.yaml`, `helm/dataobs/templates/otel-collector.yaml`, `helm/dataobs/templates/configmap.yaml`.
   - Acceptance: no secret-shaped defaults in ConfigMaps; `existingSecret` and generated secret options documented; `helm template` demonstrates env injection.

3. **P0: Add probes and pod security defaults to Helm chart**
   - Files: `helm/dataobs/templates/deployment-api.yaml`, `helm/dataobs/templates/deployment-quality.yaml`, `helm/dataobs/templates/otel-collector.yaml`, `helm/dataobs/values.yaml`.
   - Acceptance: API/collector have liveness/readiness; pods run non-root with dropped capabilities and optional read-only root filesystem; default resources are set.

4. **P0: Scan API and quality production images in CI**
   - Files: `.github/workflows/ci.yml`, `Dockerfile.api`, `Dockerfile.quality`.
   - Acceptance: Trivy scans `dataobs/api` and `dataobs/quality`; critical findings open/update issues; SARIF is uploaded.

5. **P0: Mark POC assets as non-production in docs and packaging**
   - Files: `README.md`, `docs/poc-setup.md`, `docs/poc-elastic-agent-observability.md`, `Dockerfile.poc`, `docker-compose.poc.yml`, `src/poc/README.md` if added.
   - Acceptance: every POC command clearly states local/demo use; production guide links to the supported deployment path.

6. **P0: Close Terraform bootstrap least-privilege gap for OSIS IAM**
   - Files: `infra/terraform/aws-backend/main.tf`, `infra/terraform/modules/iam/main.tf`, `infra/terraform/aws-backend/README.md`.
   - Acceptance: documented and/or automated second-stage apply replaces wildcard pipeline ARN; CI or policy check flags wildcard in production variables.

### P1 issues

7. **P1: Create typed configuration loader and validation CLI**
   - Files: new `src/config.py` or `src/core/config.py`, `src/api/main.py`, `src/quality/engine.py`, `scripts/validate_otel_config.py`, `config/dataobs.example.yaml`.
   - Acceptance: API and quality use same config model; validation command checks production config; docs explain precedence.

8. **P1: Unify store protocol and remove mixed API store routing**
   - Files: `src/api/store.py`, `src/api/es_store.py`, `src/api/main.py`, `src/quality/lineage.py`, `tests/test_api_store.py`, `tests/test_api_es_store.py`, `tests/test_lineage.py`.
   - Acceptance: one store interface covers rules, quality results, nodes, and edges; legacy paths are shimmed or migrated; tests prove tenant isolation.

9. **P1: Add API validation, pagination, and structured errors**
   - Files: `src/api/main.py`, `docs/api/rules-and-lineage-api.md`, `tests/test_api_endpoints.py`.
   - Acceptance: invalid content types and oversize bodies are rejected; list endpoints accept `limit`, `cursor` or `offset`, filters, and stable sorting; errors are consistent.

10. **P1: Add API OpenTelemetry instrumentation and structured request logging**
    - Files: `src/api/main.py`, `src/telemetry.py`, `config/otel-collector-config.yaml`, dashboards under `infra/terraform/modules/grafana-dashboards/dashboards/`.
    - Acceptance: API emits RED metrics, spans, request IDs, route/status labels, and service version resource attributes.

11. **P1: Add Helm/Terraform/static-analysis CI gates**
    - Files: `.github/workflows/ci.yml`, `pyproject.toml`.
    - Acceptance: CI runs `helm lint`, `helm template`, recursive Terraform fmt/validate, lint/type/security checks, dependency audit, and coverage.

12. **P1: Add scheduled service-backed integration tests**
    - Files: `tests/integration/**`, `.github/workflows/ci.yml` or a new workflow, `tests/integration/docker-compose.test.yml`.
    - Acceptance: manual or nightly workflow runs API + backend smoke tests and stores logs/artifacts on failure.

13. **P1: Add operations runbooks**
    - Files: `docs/production/production-guide.md`, `docs/wiki/operations-wiki.md`, new docs under `docs/production/`.
    - Acceptance: runbooks cover tenant onboarding, migrations, backups/restores, alert delivery tests, auth rotation, and rollback.

### P2 issues

14. **P2: Incrementally migrate API to ASGI/OpenAPI**
    - Files: `src/api/**`, `tests/test_api_endpoints.py`, `docs/api/rules-and-lineage-api.md`.
    - Acceptance: existing routes remain compatible; generated OpenAPI is committed or published; contract tests pass.

15. **P2: Implement OIDC/JWT/RBAC and tenant-aware authorization**
    - Files: `src/api/**`, Helm values/templates, docs/API docs.
    - Acceptance: tokens carry tenant/user claims; rule/lineage/quality endpoints enforce tenant and role checks; audit logs are emitted.

16. **P2: Move Elasticsearch/OpenSearch setup to versioned migrations**
    - Files: `src/api/es_store.py`, `config/elasticsearch/**`, `scripts/migrate_to_es.py`, Helm/Terraform bootstrap docs.
    - Acceptance: runtime no longer owns schema changes; migrations are idempotent and versioned; rollback guidance exists.

17. **P2: Package project with extras and deterministic dependency locks**
    - Files: `pyproject.toml`, `requirements*.txt`, Dockerfiles, integration requirements.
    - Acceptance: install extras exist for API, quality, POC, Spark, dbt, and Lambda; lock/constraints files drive reproducible images.

18. **P2: Publish versioned Helm chart and deployment promotion workflow**
    - Files: `.github/workflows/release.yml`, `helm/dataobs/**`, docs.
    - Acceptance: chart is linted, packaged, versioned, and tied to image tags; release notes include upgrade/rollback steps.

## Migration principles

- **Avoid sweeping rewrites.** Keep current interfaces while adding adapters, tests, and deprecation windows.
- **Start with production guards.** Prevent unsafe deployments before expanding features.
- **Separate POC from runtime.** POC code remains useful, but it should not define production defaults.
- **Prefer explicit migrations over runtime magic.** Schema/index changes should be reviewed, versioned, and repeatable.
- **Add observability before replacing internals.** Instrument the current API and store paths so future migrations are measurable.
- **Keep route compatibility.** If the API framework changes, preserve endpoints and response shapes until clients can migrate.

## Risks to track

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Production deployment accidentally runs unauthenticated API | P0 | Startup guard, Helm secret requirement, docs update. |
| Production deployment uses in-memory store | P0 | Production guard and durable default in production docs/templates. |
| Store schema drift between `store.py`, `es_store.py`, and lineage writer | P0/P1 | Unified store protocol and migration plan. |
| Secrets embedded in ConfigMaps/values | P0 | Secret references and CI checks. |
| Production images not scanned | P0 | Extend Trivy to API and quality images. |
| Helm chart renders but is not operationally hardened | P0/P1 | Probes, resources, security contexts, network policies, chart CI. |
| Terraform wildcard bootstrap permissions persist | P0/P1 | Post-bootstrap issue/check and policy scan. |
| Integration failures hidden by skipped tests | P1 | Scheduled/manual service-backed integration workflow. |
| POC code influences production defaults | P1 | Clear labels, separate dependencies, docs boundaries. |

## Quick-win checklist

- [ ] Add production startup guard for `API_TOKEN`/auth and `DATAOBS_STORE_BACKEND`.
- [ ] Add Helm `existingSecret` values and `secretKeyRef` env injection.
- [ ] Add liveness/readiness probes and default resources in Helm.
- [ ] Add Trivy scans for API and quality images.
- [ ] Add `helm lint` and `helm template` CI jobs.
- [ ] Add `ruff`, type checking, `pip-audit`, and coverage.
- [ ] Add POC/non-production warnings to POC docs and README.
- [ ] Add API readiness checks and request body validation.
- [ ] Document config precedence and production required settings.
- [ ] Create the P0 GitHub issues above and assign owners.

## Phase 0 governance correction

DataObs is not production-ready. Phase 0 requires authenticated GitHub issue disposition, container-backed integration tests, Docker Compose validation, Terraform validation, Helm validation, production Python quality gates, dependency audit, production image scanning, and SBOM generation before the PR can be marked ready.

CI now defines blocking jobs for Python quality/unit tests, Docker Compose validation, container-backed integration tests, Terraform/Helm validation, and production image security/SBOM generation. HIGH and CRITICAL fixable vulnerabilities are blocking; unfixed HIGH findings must be documented as risks rather than hidden.
