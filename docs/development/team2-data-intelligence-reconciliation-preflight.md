# Team 2 data intelligence reconciliation preflight

Recorded 2026-08-08 UTC, before production-code edits. The checkout has no configured Git remote, so the required fetch was attempted but could not contact `origin`; the newest locally available mainline commit is `e99ff14c74f0df4e65818dadd539d17ae96b0317` (it contains planning SHA `5be28cb`). This prevents a claim that the hosted repository has not advanced.

## Migration registry at audit base

Terminal migration: `0028_pathway_investigation_history`. This is the complete executable base registry; 0029 was selected only after confirming 0028 was terminal.

| Migration ID | Checksum |
|---|---|
| `0001_product_foundation` | `71d939094a97b4dd7c61de60542b60dd41cb238fd6bebfd75d53d723b00f3556` |
| `0002_postgres_observability` | `c2098fa24ddae209fcf2ffeb369f7040d57018d58682a8513db9e943c749aa2d` |
| `0003_incident_automation` | `f1f250822f94c5cc95c0b8547402a7a1294a8a3f04f1b8bd6b2713a643712ee5` |
| `0004_kafka_data_streams_monitoring` | `bf2a4cb663077d1df0be960300d04f4ad0ac2a43ab34fc0f01bf2fa40a1b32c6` |
| `0005_console_foundation` | `3b6861df951b1e4c46d0c2b6430e9327c6cf83533a7c908e0dca1cdde7793197` |
| `0006_pathway_asset_360` | `19dd1a7a5c6c36f3f807b13ca5d4785affc499cfbd53488c222b5a82b47faf10` |
| `0007_automated_monitoring_data_products_rca` | `827dd6e892a7199d4b6e91577cc3108b10045a0d67fc68375b088d20e412213e` |
| `0008_job_run_observability` | `ce32e272e9e5f7b30387cfdffbe17a403ce22fd2cffc947aea41bcddcd3e0ffe` |
| `0009_topic_queue_stream_360` | `6568576cd65fbf0f151674322506c17d95d8b361370e5a74e9bd972937eb8e95` |
| `0010_topic_queue_stream_360_completion` | `10230af88ce07b64b1e8d310065d2ae2461b4e09b8ef73c04fcf200a8f44d2cc` |
| `0011_incident_automation_workbench` | `e5ac77c3fb833c9e8380922d2d38c5e23409f1446afe6b131a137d272b6ce1aa` |
| `0012_incident_mapping_and_occ_fix` | `4ca3e9b2959b948c09879f125c5cd1de59b4b9c29df4e0f7e348c7a6316fa2b9` |
| `0013_monitor_runtime_completion` | `b8690cc9655a3992633ea57d07c9175dae90fb8dfbe602d3d4aea06155bdffef` |
| `0014_data_product_360_completion` | `7b0c111cff713342ebac7040a19a03399d9266f861749792269607b1842a7bc8` |
| `0015_data_product_360_productization` | `4bfd71dcd39336b0fcd0140589924d2f97635b90c9459f0fe5d3d6339a08155d` |
| `0016_data_product_membership_dependency_runtime` | `18ff89df0cac8777a3a72d076470a7a517b61d439e64b2b1287852a5f845178c` |
| `0017_data_product_reconciliation_retry_date` | `b34bc1859ee83a91f19bee1c96d67d1a20838149ee90dbedd56d376e0646c561` |
| `0018_data_product_decision_reason_alias` | `c01ff368f45722d80d7c5a920534e7f56fc2072831a12286a7a6a49a71eb4bb7` |
| `0019_data_product_operation_claim_expires_date` | `6ee0e71ae766305f526d7eaf91a594ae4fc8f6035ce4138b69cb618ac9912861` |
| `0020_identity_rbac_tenant_bindings` | `4b0505ec6d2e1f9db0edc19d6e7d808cff36ae2de3789dc921770b7ea3390d33` |
| `0021_lineage_analysis_explorer` | `48708bb08b183788d378f5666c19ab9d4294d073fca6df44ef1849b7af2bcd7e` |
| `0022_aws_data_platform_collector` | `adb36e8f60ffe41e85bbc910de537a6b1b415da362a9b79eda6f13f69f9f50f8` |
| `0023_stream_pathway_reliability_runtime` | `04f5ec259ee4187c4ee423b0944d7b026e27f92f20755bb71330175bfec26149` |
| `0024_job_run_reliability_runtime` | `a3a7bcbd8594a51802a6c0e3f42a98c822b708e8ae7fa68bb664f96c5472666d` |
| `0025_stream_pathway_reliability_production_closure` | `5d68f3c0acb2b265181276f3080f15d3acbf8abc39585b85715d9f5f6691fb30` |
| `0026_stream_anomaly_retention_intelligence` | `dba7efc48003dc5877af8ac2f0e6949dd44878399e9cf3e2a77043f6d1009b44` |
| `0027_platform_environment_tenant_multicluster_lifecycle` | `90b3c20f9ee44e5fa4a502e907fa3adcf3807a423ca42bad5071714d53476a25` |
| `0028_pathway_investigation_history` | `014f5406d0e063dfa1e1e51188e857028a28d6518d79a3a4907df783ea13d092` |

## Git-history collision evidence

| Point in history | Migration ID | Migration name | Checksum | Merge SHA |
|---|---|---|---|---|
| PR #223 side commit | 0026 | lineage impact/change intelligence | `9ae0dcb020fce377b8f48e0a6d4c7a83e0b3bc63e7ad36fac7b701437235b223` | `b231b1806cf7c80189e7455729ffc8a58ca6ef02` |
| PR #224/225 mainline | 0026 | stream anomaly retention intelligence | `dba7efc48003dc5877af8ac2f0e6949dd44878399e9cf3e2a77043f6d1009b44` | `ee8bb0363df503e60c85136f6d46ecb6ce606633` / `0b11c7e7c534d56cf0e89343bca9c25d579d4af2` |
| PR #226 side commit | 0027 | data contracts schema governance | `a2a6cf19a727c66d19c52ee2d639f16bbe6e914f0900271d55cf7098b0a614ce` | `3b439c4826362dbf8c347c8e828139481feaf101` |
| PR #229 mainline | 0027 | platform environment tenant multicluster lifecycle | `90b3c20f9ee44e5fa4a502e907fa3adcf3807a423ca42bad5071714d53476a25` | `70f77d85b17776fe2222d591788f145269479057` |
| PR #232 mainline | 0028 | pathway investigation history | `014f5406d0e063dfa1e1e51188e857028a28d6518d79a3a4907df783ea13d092` | `80f6935` |

Git objects prove both Team 2 definitions existed on merged side commits. Later parallel branches reused their IDs and conflict resolution left only stream/platform definitions in the final list. They were not renamed or replaced by equivalent resources: service writers still name resources absent from the base registry. This is an overwrite/drop during parallel stale-branch reconciliation. PR #233 merged as `e467adfb652fd2f5f66af7f01cbda4f89c264ae9` and did not repair them.

## Surface inventory

* Lineage files: `services/lineage_intelligence/models.py`, `repository.py`, `elasticsearch_repository.py`, `traversal.py`, `schema_diff.py`, and `impact.py`. `src/api/lineage_routes.py` is registered by `src/api/app.py`; Console registers `/lineage` only.
* Contract files: `services/data_contracts/models.py`, `repository.py`, `elasticsearch_repository.py`, `lifecycle.py`, `schema_rules.py`, and `evaluator.py`. Console registers all four contract routes. No Contract API router or durable runtime CLI is registered.
* Adaptive files: `services/monitoring/adaptive_engine.py`, `distribution_drift.py`, baseline repository/service/engine, and evaluation service. Monitor API is registered; no dedicated anomaly Console route exists.
* Generated state: `openapi.json` has lineage change/impact endpoints but lacks Contract and requested adaptive inventory endpoints. The generated TypeScript client exists under `ui/dataobs-console/src/api/generated`.
* Ledger/matrix: 46 generated capabilities; distinct Team 2 v1 entries are absent and `/quality/*` is a declared route family. `feature-matrix.md` is generator-owned.
* CI: `lineage-analysis-console.yml`, `data-quality-console-v1.yml`, `data-quality-monitoring.yml`, `adaptive-data-anomaly-detection-v1.yml`, and `job-run-backend.yml` are relevant.
* Helm/package: generic API/worker packaging exists; no dedicated Lineage/Contract worker deployment exists because those CLIs are absent.
* Shared files: the migration manifest/registry/CLI, API app/OpenAPI, typed Console routes, capability ledger, Helm, and certification workflows cross Team 0 boundaries.

## Recovery recommendation

Preserve 0001–0028 byte-for-byte. Add one 0029 reconciliation containing only resources named by existing readers/writers, fail closed before operations on checksum/name ambiguity, expose a read-only doctor, and require audited Team 0-approved manual recovery for divergent clusters. Never rewrite migration state automatically.
