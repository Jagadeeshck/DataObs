# First MVP: realistic same-day target

Date: 2026-10-26. Baseline: `ed923635b85ee38fa966a73d499883a260b9a535`.

## Definition of today's MVP

Today's achievable target is a reproducible **local evaluation stack**, not a
production release or supported-platform certification. It consists of:

1. Elasticsearch 9.5.5 with persisted local storage and bounded readiness.
2. The released 33-migration graph applied before the API starts.
3. The DataObs 0.2.0 API using Elasticsearch as its authoritative store.
4. The built Console served by unprivileged Nginx and proxying `/api/` to the API.
5. Required, operator-supplied local credentials; no committed secret defaults.
6. Container health checks, non-root application images, read-only application
   filesystems, and `no-new-privileges` on the application services.

Start it with:

```bash
cp .env.mvp.example .env.mvp
# Replace both placeholder secrets in .env.mvp.
./scripts/demo_mvp.sh config
./scripts/demo_mvp.sh up
./scripts/demo_mvp.sh status
```

The Console is at <http://localhost:3000>; the API health endpoint is at
<http://localhost:8080/health>. Tear down with `docker compose --env-file
.env.mvp -f docker-compose.mvp.yml down`. Add `--volumes` only when intentionally
discarding evaluation data.

The presenter checklist and ten-minute narrative are in the
[first-MVP demo runbook](../demo/first-mvp-demo.md).

## Exit criteria for today

- Shared backend and Console foundation checks pass.
- Helm lint targets the chart's declared Kubernetes 1.30 support window.
- Python and Console dependency audits have no high/blocking finding.
- `docker compose ... config` succeeds with operator-supplied secrets.
- API, migration, Console, and Elasticsearch images build successfully in hosted
  CI or a Docker-capable workstation.
- A smoke run records health and migration results without claiming hosted,
  independent, security, or production certification.

## Explicitly deferred

- Production TLS, external OIDC, backup/restore, HA, Kubernetes certification,
  live cloud credentials, and a supported-platform declaration.
- Kafka mapping evolution and the known Team 5 Playwright/accessibility defects.
- Release authorization. Product truth remains version 0.2.0, `NO_GO`, security
  `INCOMPLETE`, and supported platforms `[]` until exact-SHA hosted evidence says
  otherwise.

