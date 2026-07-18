# CI validation policy

Phase 0 CI is blocking for pull requests and `main` pushes. Python quality checks run Ruff, Black, focused Ruff/Black checks on maintained Phase 0 scanner and integration-test code, production-package mypy for `packages/agent_sdk` and `services/scanner_worker`, `compileall`, dependency audit, and pytest. Historical POC/demo code is intentionally excluded from new formatter/type gates until the planned product restructuring migrates or isolates those modules; `compileall` and pytest still cover them for syntax and regression safety.

The `integration-tests` job starts Elasticsearch 9.4.2, the OpenTelemetry Collector, the DataObs API, and a mock webhook service, then runs the service-backed tests with `RUN_INTEGRATION_TESTS=1`. Failures upload JUnit results and Compose logs.

Docker Compose validation fails on invalid maintained Compose files. Terraform validation runs `fmt`, `init -backend=false`, and `validate` for every maintained Terraform root/module. Helm validation runs `helm lint` and `helm template`.

Security scans build the production API and quality-worker images and fail on fixable CRITICAL and HIGH vulnerabilities. HIGH severity findings are blocking unless the vulnerability is unfixed by the upstream package or image; those are tracked as risk items rather than masked. SBOMs are generated as CycloneDX artifacts for production images.
