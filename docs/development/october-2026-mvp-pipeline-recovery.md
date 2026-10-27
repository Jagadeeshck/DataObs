# October 2026 MVP pipeline recovery

Audit date: 2026-10-26. Audited main SHA:
`ed923635b85ee38fa966a73d499883a260b9a535`.

## Hosted failure classification

| Workflow | Run | First meaningful failure | Classification | This change |
|---|---:|---|---|---|
| Team delivery foundation | [40349886162](https://github.com/Jagadeeshck/DataObs/actions/runs/40349886162) | Console high-severity audit found vulnerable transitive `zod` | shared dependency | Override `zod>=4.6.6`; retain the high-severity gate |
| Team 4 RabbitMQ messaging collector v1 | [40349885955](https://github.com/Jagadeeshck/DataObs/actions/runs/40349885955) | `pip-audit` found vulnerable CI tooling | shared dependency | Upgrade Black and audit the declared runtime/CI inputs deterministically |
| Team 0 deployment packaging | [40349886084](https://github.com/Jagadeeshck/DataObs/actions/runs/40349886084) | `helm lint` used Helm's moving default Kubernetes version outside the chart's declared 1.30 window | shared orchestration | Pass the certified target `--kube-version 1.30.0` everywhere the chart is linted |
| Connector and Schema 360 | [40349886121](https://github.com/Jagadeeshck/DataObs/actions/runs/40349886121) | backend mypy and Elasticsearch-backed exact-commit stages | domain validation | Not represented as fixed by the shared changes |
| Pathway Intelligence backend | [40349886001](https://github.com/Jagadeeshck/DataObs/actions/runs/40349886001) | apply existing Elasticsearch migrations | domain mapping/runtime | Deferred; do not delete indices or weaken mapping validation |
| Console Product Experience | [40349885954](https://github.com/Jagadeeshck/DataObs/actions/runs/40349885954) | Playwright/axe cross-capability smoke | Team 5 product quality | Deferred; axe and browser checks remain enabled |
| Administration access Console | [40349885986](https://github.com/Jagadeeshck/DataObs/actions/runs/40349885986) | browser/accessibility/mock OTLP journey | Team 5 product quality | Deferred |

Downstream evidence verification failures caused by a producer job that did not
emit evidence are cascades, not additional product defects. No hosted result is
claimed for this branch until its workflows execute.

## Same-day MVP target

The first MVP is the bounded local evaluation stack documented in
[`first-mvp-today.md`](first-mvp-today.md). It deliberately targets one API,
one Console, one Elasticsearch node, and an ordered migration init container.
It is not a production topology, supported-platform certification, or release
authorization.

## Product truth

Application version remains 0.2.0. The terminal migration is derived from the
registry. Security remains `INCOMPLETE`, release remains `NO_GO`, and supported
platforms remain empty. Local Docker validation cannot change those states.

