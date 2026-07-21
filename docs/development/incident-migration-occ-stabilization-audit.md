# Incident migration and OCC stabilization audit

## Baseline and evidence

The audited checkout is `8638914a549f110c1f67e069bb937b221390a88b` (`main` at prompt creation). The checkout has no configured Git remote, so `git fetch main` and the unresolved PR #103 P1 review threads could not be retrieved; this remains an external-evidence blocker. The branch was created from the exact observed SHA.

The released migration chain and SHA-256 operation checksums are:

| ID | Dependency | Checksum |
|---|---|---|
| 0001_product_foundation | — | `71d939094a97b4dd7c61de60542b60dd41cb238fd6bebfd75d53d723b00f3556` |
| 0002_postgres_observability | 0001 | `c2098fa24ddae209fcf2ffeb369f7040d57018d58682a8513db9e943c749aa2d` |
| 0003_incident_automation | 0002 | `f1f250822f94c5cc95c0b8547402a7a1294a8a3f04f1b8bd6b2713a643712ee5` |
| 0004_kafka_data_streams_monitoring | 0003 | `bf2a4cb663077d1df0be960300d04f4ad0ac2a43ab34fc0f01bf2fa40a1b32c6` |
| 0005_console_foundation | 0004 | `3b6861df951b1e4c46d0c2b6430e9327c6cf83533a7c908e0dca1cdde7793197` |
| 0006_pathway_asset_360 | 0005 | `19dd1a7a5c6c36f3f807b13ca5d4785affc499cfbd53488c222b5a82b47faf10` |
| 0007_automated_monitoring_data_products_rca | 0006 | `827dd6e892a7199d4b6e91577cc3108b10045a0d67fc68375b088d20e412213e` |
| 0008_job_run_observability | 0007 | `ce32e272e9e5f7b30387cfdffbe17a403ce22fd2cffc947aea41bcddcd3e0ffe` |
| 0009_topic_queue_stream_360 | 0008 | `6568576cd65fbf0f151674322506c17d95d8b361370e5a74e9bd972937eb8e95` |
| 0010_topic_queue_stream_360_completion | 0009 | `10230af88ce07b64b1e8d310065d2ae2461b4e09b8ef73c04fcf200a8f44d2cc` |
| 0011_incident_automation_workbench | 0010 | `e5ac77c3fb833c9e8380922d2d38c5e23409f1446afe6b131a137d272b6ce1aa` |

Regression tests pin the order, dependencies, and checksums rather than relying on release notes.

## Mapping gap

An already-applied 0003 cluster retains the concrete mapping created at that time because the registry only invoked index creation when the concrete index was absent. Its strict mapping therefore did not gain later canonical document fields. The historical compatible core was tenant/environment and product metadata plus early identifiers, severity, state, and observation timestamps. Current serialization also writes the following relevant fields:

* Finding: `id`, source event/version, finding/signal type, asset/scanner/monitor/policy/rule identifiers, title/summary, observed/expected values, evidence, downstream impact/count, confidence, tracing/request identifiers, observation/recovery timestamps, resources/data products, correlation features, and suppression/recovery state.
* Incident: `id`, state/severity/deduplication/correlation, title, finding and affected-asset arrays, root-cause candidates, impact and severity scoring, occurrence count, evidence, workflow/case/external references, lifecycle timestamps/reasons, priority/urgency/impact, ownership/collaboration fields, recovery/recurrence/merge/split fields, plus inherited product metadata.

`seq_no` and `primary_term` are transport metadata and are explicitly excluded from indexed incident documents. All other fields are represented by explicit strict mapping properties. The missing properties are additive and do not redefine an existing type, so 0012 uses `put_mapping`; a pre-existing incompatible type causes a hard failure before migration state is written.

## Read/write and concurrency audit

Mutation-capable reads are `find_incident_by_dedup`, direct `get_incident` used by transition and assignment, and incident list/search results that callers may subsequently mutate. Direct gets already return Elasticsearch concurrency metadata. Both incident search paths now request `seq_no_primary_term`; the dedup query independently filters tenant, environment, and key.

Before this change, `save_incident` indexed with OCC only when tokens happened to be present and otherwise silently overwrote or upserted. Ingest, transition, and assignment all reached that ambiguous write. They now use create-only writes or token-required updates. Elasticsearch conflicts become the stable `VersionConflict` domain error and API mutations return a redacted 409 envelope.

Ingest retries at most three times. Each retry reloads current state and applies a pure merge. A finding ID increments occurrence count only when newly linked; IDs and affected assets are sorted unique. Evidence and the last-observed timestamp change only when the incoming finding timestamp is at least the stored timestamp.

## Migration safety

0012 targets only the registry-owned concrete indices `dataobs-findings-v1` and `dataobs-incidents-v1`. It verifies existence and `dynamic: strict`, rejects incompatible installed types, applies explicit properties, reads the mapping back, and verifies types before recording success. Missing indices cannot be auto-created. A successful rerun reads the existing checksum record and performs no writes.

Failure leaves aliases and documents intact and does not record 0012. Retry is the same plan after correcting the incompatible or missing index. Mapping additions cannot be removed safely; rollback is application rollback after snapshot, or forward repair/reindex if an incompatible field is discovered. Operators must not delete incident/finding indices as routine rollback.

## Commands and results

* `git log -5 --oneline --decorate`: checkout at `8638914` with PR #104 merge history.
* `python -m pytest tests/unit/test_incident_automation.py tests/unit/test_incident_workbench_safety.py tests/elastic_store/test_migrations.py -q`: initial audit run found two expected stale assertions; both were corrected for 0012 ordering and replay idempotency.
* Final focused and real-Elasticsearch results are recorded in the PR description and final change summary. A hosted required-job URL is unavailable until the draft PR runs in GitHub Actions.

## Remaining blockers

The missing Git remote prevents independent latest-main fetch and PR #103 review-thread inspection. A local Docker test is evidence only for this checkout; the PR must remain draft until the dedicated hosted CI job succeeds and provides its run URL and artifacts.
