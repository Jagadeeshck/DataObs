---
inclusion: manual
---

# First Release Execution Plan — v1.0.0 (week of 2–6 Nov 2026)

> **Internal working document.** Concrete step-by-step execution guide for the release
> week. References the spec tasks in `.kiro/specs/first-release-week/tasks.md`.

## Release decision criteria (all must be true for GO)

1. All mandatory Gate 0 CI jobs green on exact frozen SHA
2. `beta-1-certification-manifest.yaml` producers pass with `expected_elasticsearch_version: 9.5.5`
3. Security gate: OIDC hosted, tenant isolation hosted, SBOM/provenance/signatures present
4. Browser/accessibility: Playwright + axe zero serious/critical violations on release-critical journeys
5. Backup/restore: destructive restore succeeds with tenant isolation verified
6. Helm: lint + Kind smoke + upgrade + rollback pass
7. Independent verifier accepts each artifact/run/attempt
8. Protected release authority returns GO

**Any failure = NO_GO. No partial release claims.**

---

## Daily execution

### Monday 2 Nov — triage

**Morning (Team 0):**
```bash
cd DataObs
git checkout release/v1.0.0-elastic-9.5.5
# Trigger CI on the release branch via GitHub Actions workflow_dispatch
# Check: ci.yml jobs — what's failing?
```

Triage checklist:
- [ ] Run `docker compose --env-file .env.mvp.example -f docker-compose.mvp.yml up --build`
      — does it start cleanly from scratch?
- [ ] Check `packages/elastic_store/cli.py plan` output — does it show 33 migrations?
- [ ] Verify `scripts/release/release_metadata.py` terminal migration matches manifest
- [ ] Confirm Helm Chart.yaml `version: 1.0.0`, `appVersion: "1.0.0"` ✅ done
- [ ] Confirm `openapi.json` `info.version: 1.0.0` ✅ done
- [ ] Classify all CI failures: shared infra / domain / browser / supply-chain

**All teams in parallel:** read CI failure logs, identify owned blockers.

---

### Tuesday 3 Nov — shared fixes

**Team 0 priorities:**
1. Fix any shared CI failures (migrations, API startup, Helm, Compose)
2. Trigger `beta-backup-restore.yml` — does it pass against ES 9.5.5?
3. Start `beta-security-hardening.yml` — does OIDC fixture work?

**Team 5:**
1. Fix Console build/typecheck failures if any
2. Run Playwright + axe locally against MVP stack
3. Check bundle size (bundle-check script)

**Team 2:**
1. Run quality signal path locally: create monitor → trigger evaluation → check finding created
2. Run `data-quality-monitoring.yml` workflow manually

**Team 1:**
1. Run `docker compose -f docker-compose.kafka-observer-real-stack.yml up`
2. Verify Kafka observer connects, indexes cluster/topic/consumer-group data

---

### Wednesday 4 Nov — merge and revalidate

Merge order (strict — each merge invalidates SHA-based evidence):
1. Team 0 shared fixes (if blocking)
2. Team 5 Console fixes
3. Team 2 domain fixes
4. Team 1 domain fixes
5. Team 3/4 only if a mandatory defect

After each merge: re-run mandatory Gate 0 checks.

---

### Thursday 5 Nov — freeze and certify

**By 12:00:** last source merge. Freeze candidate SHA.

**Afternoon — dispatch canonical producers:**
```
beta-security-hardening.yml         → workflow_dispatch on frozen SHA
beta-deployment-packaging.yml       → workflow_dispatch
beta-backup-restore.yml             → workflow_dispatch
stream-observer-backend.yml         → workflow_dispatch
pathway-intelligence-backend.yml    → workflow_dispatch
data-quality-monitoring.yml         → workflow_dispatch
job-run-backend.yml                 → workflow_dispatch
lineage-analysis-console.yml        → workflow_dispatch
incident-workbench-certification.yml → workflow_dispatch
console-product-experience.yml      → workflow_dispatch (browser/a11y)
integration-sdk-certification.yml   → workflow_dispatch
```

**Independent verifier:** for each artifact:
- Verify artifact digest matches the run that produced it
- Verify `producer_sha` matches the frozen candidate SHA
- Verify `workflow_run_attempt` is ≥1 and not a rerun that hid a failure
- Verify `elasticsearch_version: 9.5.5`
- Verify no mandatory test category is marked `skipped`

---

### Friday 6 Nov — release decision

**09:00:** Team 0 collects all evidence artifacts.

Run `scripts/release/gate0.py --sha <frozen-sha> --repo Jagadeeshck/DataObs`

If all producers return `success` and independent verification passes:

```bash
# Tag the release
git tag -s v1.0.0 <frozen-sha> -m "DataObs v1.0.0 — first supported release"
git push origin v1.0.0

# Publish images (CI handles this via the release workflow)
# Images: dataobs-api:1.0.0, dataobs-console:1.0.0, etc.
```

If any gate fails: issue NO_GO report. Document blockers in
`evidence/v1.0.0-no-go-report.md`. Do not tag. Do not publish.

---

## Local verification commands

```bash
# 1. Clean start from scratch
docker compose --env-file .env.mvp -f docker-compose.mvp.yml down -v
docker compose --env-file .env.mvp -f docker-compose.mvp.yml up --build

# 2. Verify migrations applied
curl http://localhost:8080/health
curl -H "Authorization: Bearer $DATAOBS_API_TOKEN" http://localhost:8080/platform/lifecycle/release

# 3. Verify Console loads
open http://localhost:3000

# 4. Run unit tests
python -m pytest tests/unit tests/elastic_store tests/data_products -q

# 5. Run docker compose config validation (all 4 main stacks)
ELASTIC_PASSWORD=test KIBANA_PASSWORD=test OPENSEARCH_PASSWORD=test \
  docker compose -f docker-compose.yml config --quiet && echo "✅ main"
docker compose --env-file .env.mvp.example -f docker-compose.mvp.yml config --quiet && echo "✅ mvp"
ELASTIC_PASSWORD=test KIBANA_PASSWORD=test CERTIFICATION_POSTGRES_PASSWORD_FILE=/tmp/pg \
  docker compose -f docker-compose.certification.yml --profile full config --quiet && echo "✅ cert"
ELASTIC_PASSWORD=test KIBANA_PASSWORD=test APM_SECRET_TOKEN=test \
  docker compose -f docker-compose.poc.yml config --quiet && echo "✅ poc"

# 6. Check migration terminal
python -m packages.elastic_store.cli plan | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('Terminal migration:', d[-1]['migration_id'])
print('Total migrations:', len(d))
"

# 7. Verify version consistency
python3 - <<'PY'
import json, pathlib
chart = pathlib.Path('helm/dataobs/Chart.yaml').read_text()
openapi = json.load(open('openapi.json'))
pkg = json.load(open('ui/dataobs-console/package.json'))
es = pathlib.Path('requirements.txt').read_text()
assert 'version: 1.0.0' in chart, 'Chart.yaml version wrong'
assert 'appVersion: "1.0.0"' in chart, 'Chart.yaml appVersion wrong'
assert openapi['info']['version'] == '1.0.0', f"OpenAPI version wrong: {openapi['info']['version']}"
assert pkg['version'] == '1.0.0', f"Console package version wrong: {pkg['version']}"
assert 'elasticsearch[async]==9.5.0' in es, 'ES client version wrong'
print('✅ All version checks pass')
PY
```

---

## Evidence artifact checklist

Each mandatory producer must generate an artifact containing:
- `producer_sha` — exact frozen SHA
- `elasticsearch_version` — `9.5.5`
- `terminal_migration` — `0033_team1_stream_schema_intelligence_runtime`
- `workflow_run_id` and `workflow_run_attempt`
- JUnit XML file(s) — no mandatory test `skipped`
- `independent_verification: required` or `pending` (not `rejected`)

Artifacts tracked in `docs/release/beta-1-certification-manifest.yaml`.
