# PR #108 certification runtime completion audit

PR #108 merged at `b1b8cc4`. Migrations 0001–0012 remain immutable; this change adds no migration.

| Capability | PR #108 state | Runtime blocker | Required correction | Hosted evidence |
|---|---|---|---|---|
| API internal/listening port | API used 8080 | Nginx used 8000 | Canonical API 8080; hosts 18000/18080 | Runtime contract and proxy health |
| Console proxy | Misaligned | `/api` returned 502 | Fixed upstream, forwarded request/trace headers, bounded timeouts | Browser and runtime contract jobs |
| Production Console | Image existed | Certification could bypass it | Browser infrastructure builds and serves the Nginx image | Playwright report |
| Browser base URL / web server | Local Vite preview | Production defects masked | External 18080 config with no `webServer` | Browser JUnit, trace, screenshots |
| Vite build | Not independently assured | Preview had no guaranteed build | CI must run frozen install, generate, typecheck and build | Console build log |
| Scanner configuration / secret | Example localhost database and env indirection | Scanner could not reach fixture | Read-only mounted certification config and `file://` secret | Scanner log and PostgreSQL/API assertions |
| PostgreSQL fixtures | Composed `orders` database | Scanner targeted another database | Use `postgres/orders/dataobs_fixture`; deterministic init remains required | Backend JUnit |
| Kafka bootstrap / Observer | Brokers composed, observer implicit | Configuration and live depth incomplete | Explicit bounded observer configuration and live assertions remain required | Backend JUnit |
| Connect / Schema Registry | No health gates | Start order was treated as readiness | Meaningful health checks and deterministic internal topics remain required | Service-health artifact |
| OpenLineage delivery | Presence-only test | No endpoint assertion | Live endpoint/storage assertions remain required | Backend JUnit |
| Seed / migration | Scaffolded | Idempotency not hosted | Apply and seed twice in backend workflow | Timing and backend reports |
| Backend depth | Presence checks | No provider behaviour proved | Shared live clients and depth meta-test remain required | Backend JUnit |
| Browser depth / axe | Scaffolded | Did not prove production assets/API | Production Nginx journeys and machine-readable axe results | Browser artifacts |
| Security startup | Tests lacked stack | Runtime scenarios could not execute | Start core plus security infrastructure | Security JUnit/SBOMs |
| Evidence redaction / hashes | Hash before redaction | Retained bytes invalidated hashes | Redact, scan, build manifest, then verify | Verified final manifest |
| Downloaded artifacts | Flat handling risk | Duplicate names could overwrite | Preserve job-origin directories recursively | Summary artifact tree |
| Hosted metadata | Local-compatible manifest | Local output could look promotable | Hosted run ID/URL required for promotion; local fields null | Summary manifest |
| Capability promotion | Proposal tooling existed | Scaffold could overclaim | Proposal only, reviewed ledger commit, blockers retained | Promotion proposal |

The certification gate validates only the capabilities and dimensions named in its retained evidence. It does not make DataObs as a whole production-ready.

## Current limitation

This commit closes the five concrete runtime contract defects and makes final evidence hashes verifiable. Provider-depth, hosted-run, and capability-promotion rows above deliberately remain unclaimed until a real hosted run produces retained evidence.
