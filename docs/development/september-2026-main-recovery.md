# September 2026 main recovery

## Starting state

Inventory was taken on 2026-09-13. The requested `git fetch origin` could not run because this supplied checkout has
no `origin`; the local `main` checkpoint was nevertheless exactly the expected
`469030b685b289b959bae952c58d89cb2664a331`. Work started from that commit on
`codex/team0-september-rebaseline-main-recovery` with a clean tree.

| Item | Observed truth |
| --- | --- |
| Application / chart | `0.2.0` / `0.2.0` |
| Python / Node / pnpm | `3.14.4` / `24.15.0` / `10.28.1` locally; CI declares Python 3.11, Node 22 and pnpm 10.28.1 |
| Elasticsearch target | server `9.5.5`; client is now constrained to compatible `9.4.x` |
| Terminal migration | `0033_team1_stream_schema_intelligence_runtime` (33 migrations, dynamically discovered) |
| Release / security / platforms | `NO_GO` / `INCOMPLETE` / `[]` |
| Main push workflows | 25 triggered: 4 passed, 21 failed, 0 cancelled (downstream skipped jobs are not separate defects) |
| Pull requests | one open (#291); recent merges #289, #290, #288, #287 and #286 |

The workflow totals and first failing steps below come from the public Actions API for exact SHA `469030b6` (run IDs
link to GitHub). Job logs were not downloadable without credentials, so supplied failure messages are identified as
such rather than reconstructed.

## Failure inventory

Root causes: **A** shared CI/bootstrap/orchestration, **B** product defect, **C** test/evidence contract,
**D** environment/external dependency, **E** secret/configuration dependency, **F** fail-closed policy.

| Workflow (run) | First meaningful job / step | Root cause and owner | Scope / cascade | Status after repair |
| --- | --- | --- | --- | --- |
| [Team delivery foundation](https://github.com/Jagadeeshck/DataObs/actions/runs/31910540017) | backend / Mypy; console / Exact-commit evidence | B Team 1 typing; A Team 0 evidence import | shared roots | Named defects repaired; broader `mypy src` still has 44 baseline errors and hosted rerun is blocked |
| [RabbitMQ](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539870) | validate / migration immutability (`--base-ref required`) | A Team 0 | shared | Canonical resolver applied |
| [Console Product Experience](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539908) | exact evidence / Playwright and axe (10/15 failed) | B Team 5 | domain | Current browser rerun required |
| [Deployment packaging](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539866) | validate / Helm lint | B Team 0; verifier is downstream cascade | domain | Hosted rerun required |
| [Stream 360](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539898) | verify / apply and seed migrations | A Team 0 readiness | shared | Bounded readiness retained; hosted rerun required |
| [Security hardening](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539857) | security / apply migrations | A Team 0 readiness | shared | Bounded readiness retained; hosted rerun required |
| [Pathway Intelligence](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539872) | verify / apply migrations | A Team 0 readiness | shared | Bounded readiness retained; hosted rerun required |
| [Stream observer](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539888) | certify / bounded results | C Team 1; verifier cascaded | domain | Hosted rerun required |
| [Administration Console](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539894) | validate / browser and accessibility | B Team 5 | domain | Hosted rerun required |
| [Data Product foundation](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539916) | Elasticsearch migrations; security apply | A Team 0 readiness; summary cascaded | shared | Hosted rerun required |
| [Console observability](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539884) | validate / browser and accessibility | B Team 5 | domain | Hosted rerun required |
| [Job runs](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539883) | evidence verification | C Team 2 | domain | Hosted rerun required |
| [Data quality](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539899) | evidence verification | C Team 2 | domain | Hosted rerun required |
| [Data Product reconciliation](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539885) | Elasticsearch apply | A Team 0 readiness; summary cascaded | shared | Hosted rerun required |
| [Connector / Schema 360](https://github.com/Jagadeeshck/DataObs/actions/runs/31910540033) | migration/ES evidence; reusable browser/backend | A plus Team 1/5 cascades | shared | Shared repairs applied; rerun required |
| [Backup restore](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539905) | evidence envelope | A Team 0 metadata dependency | shared | Minimal import boundary repaired |
| [Pathway Explorer](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539892) | boundaries/migrations/backend | A/B Team 0/1 | shared cascade | Resolver and typing repaired locally |
| [Data quality Console](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539911) | browser; evidence verifier | B Team 5; verifier cascaded | domain | Hosted rerun required |
| [Kafka Cluster 360](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539998) | migrations; reusable Console/backend | A plus Team 1/5 cascades | shared | Shared repairs applied; rerun required |
| [Lineage Console](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539877) | browser; evidence verifier | B Team 5; verifier cascaded | domain | Hosted rerun required |
| [CI](https://github.com/Jagadeeshck/DataObs/actions/runs/31910539867) | type check, Terraform, actionlint, OCC | A/B mixed, Team 0/1/3 | mixed | Canonical base repair applied; residuals require hosted logs/rerun |

Four exact-SHA push workflows passed: Incident Workbench, IAM/OIDC, Azure collector, and Integration SDK. These are
useful canaries, not proof that downstream release or security certification passed.

## Shared CI repairs

* **Dependency bootstrap:** hosted Python product tests continue to install `requirements.txt` and
  `requirements-ci.txt`; regression tests reject missing files and CI-only test environments.
* **Console evidence boundary:** `packages.elastic_store` now exposes registry operations lazily. Pure manifest and
  release metadata imports therefore do not load the Elasticsearch client. Isolated subprocess tests enforce this for
  both release metadata and the Console evidence writer.
* **Migration base/history:** every ordinary workflow immutability invocation uses `scripts/resolve_ci_base.py`.
  Candidate workflows retain explicit reviewed candidate inputs. The resolver handles PR, push and dispatch events,
  validates ancestry, rejects `base == HEAD`, diagnoses shallow history, and permits root bootstrap only explicitly.
  All history-dependent jobs retain full-depth checkout.
* **Elasticsearch readiness:** the bounded cluster-health and indices probe remains before application interaction;
  it retries transient disconnects and exits nonzero on timeout. No sleep replaces readiness.
* **Version decision:** the product server remains `9.5.5`. Allowing any 9.x client made hosted resolution
  nondeterministic (9.5.0 was observed), so both canonical and POC requirements constrain the client to
  `==9.4.1`, the latest published 9.4 Python client compatible with the Elasticsearch 9.5.5 server target.

## Genuine product defects

### Team 1

The current Stream Intelligence route/service models use explicit request and response types and pass focused Mypy.
That repair at the starting checkpoint is preserved; it was not weakened or excluded during the CI recovery.

### Team 5

Hosted Playwright is real execution, not `not_run`. The prior run's accessibility, keyboard focus, accessible-name,
Product 360 and supportability findings remain product defects until the current branch executes the 15-test browser
suite successfully. Axe rules and RBAC negative coverage remain enabled.

## Hosted results

No hosted run can exist for the unpushed recovery commit in this environment (no remote or GitHub credential). The
starting-SHA canaries are: Team Delivery Foundation run `31910540017` **failed**; security hardening `31910539857`
**failed**; Console Product Experience `31910539908` **failed**; RabbitMQ `31910539870` **failed**; Azure collector
`31910539924` **passed**; Incident Workbench `31910539919` **passed**. Exact recovery-SHA hosted canaries are required
before nomination.

## Remaining blockers

* **Code:** `mypy src` still reports 44 errors across 16 pre-existing modules outside Stream Intelligence. Browser
  execution also needs a current runnable result; plus any residual Helm, Terraform, actionlint, OCC,
  evidence-contract, or Elasticsearch failures found by recovery-SHA hosted reruns.
* **Configuration/secrets/external:** authenticated GitHub push/rerun access and any real certification credentials;
  no fake secret evidence is acceptable.
* **Release certification:** exact-SHA security PASS and supported-platform certification do not exist.
* **Independent verification:** remains false; same-workflow checksum/provenance validation is not independent.

The product remains `0.2.0`, `INCOMPLETE`, `NO_GO`, with no supported production platforms. Historical candidate
metadata is not reinterpreted as a candidate for this recovery SHA.
