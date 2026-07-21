# PR #110 hosted certification follow-up

PR #110 is present in the repository history at merge commit `649f768`. The checkout has no
configured Git remote and does not provide `gh`, so hosted runs, review-thread replies, and a
real evidence manifest remain administrative blockers. This pull request must remain draft.

| Finding | Root cause | Fix | Test | Hosted job | Evidence |
|---|---|---|---|---|---|
| Migrations absent | Focused stacks started directly before tests. | Every write-backed job applies and verifies migrations; the migration job applies twice. | Workflow semantics and migration tests | Pending | Pending hosted artifact |
| Invalid Observer config | The file used legacy, forbidden fields and scalar brokers. | The checked-in file now validates against `KafkaObserverConfig`; service locations remain environment-driven. | `test_kafka_observer_config.py` | Pending Kafka | Pending |
| Kafka unseeded | Tests followed broker startup without fixtures. | Topics, schemas, connectors, producers, and consumers run before assertions. | Workflow ordering and Kafka tests | Pending Kafka | Pending |
| Focused summary rejected skips | Summary required all jobs regardless of dispatch scope. | A checked Python policy requires selected successes and unrelated skips and marks focused results partial. | `test_workflow_scopes.py` | Pending each scope | Pending |
| Product scope skipped | Product was omitted from the OpenLineage/product condition. | The condition explicitly selects `all`, `openlineage`, and `product`. | `test_product_selects_product_job` | Pending product | Pending |

## Conservative status

No capability is promoted by this local change. Release readiness remains **blocked**. The
successful all-scope run closes the Phase B certification baseline only for the named
capabilities and validation dimensions. DataObs as a whole remains blocked from production
readiness. That statement becomes evidence-backed only after the pending successful hosted
all-scope run and retained, hash-verified artifacts.
