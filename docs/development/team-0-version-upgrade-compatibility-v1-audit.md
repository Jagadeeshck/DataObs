# Team 0 version upgrade compatibility v1 audit

* **Audited main SHA:** `39b7757a8cce5634bf84f17da53d745f59eefc6b`
* **Application / Helm chart:** `0.2.0` / `0.2.0` (canonical `helm/dataobs/Chart.yaml`).
* **Release decision:** `NO_GO`; supported platform list is empty.
* **Terminal migration:** `0032_team2_data_slo_production_runtime`, graph-derived.
* **Migration integrity:** 32 IDs and ordinals; no duplicates, missing/future dependencies, cycles, branches, checksum conflicts, or ambiguous leaves. Runtime identity is the immutable full ID persisted in `dataobs-system-migrations-v1`; the existing immutability guard compares IDs/checksums/dependencies. No reconciliation was required.
* **Kubernetes:** chart constraint `>=1.30.0-0 <1.31.0-0`; certification remains pending.
* **Elasticsearch:** exact candidate `9.4.2`; unvalidated.
* **Runtimes:** release workflow Python 3.13; Console Node 22. Other CI runtimes are not support claims.
* **Helm:** chart API v2, client 3.17 profile is unvalidated; values schema declares draft-07 contract and schema version 1.0.
* **OIDC:** Authorization Code + PKCE S256 contract with issuer, audience and signing-key validation; hosted conformance pending.
* **API / lifecycle:** OpenAPI 3.1.0; platform environment lifecycle models are v1 and the compatibility contract is version 1.0.
* **Providers:** implementation metadata remains authoritative; the product registry defaults to unvalidated.
* **Existing tooling:** migration CLI/registry, immutability check, terminal derivation, Helm renderer, release-decision and readiness renderers, lifecycle API, backup/restore workflows and rollback/upgrade runbooks are reused.
* **Deprecation / evidence:** there was no canonical public deprecation registry. Upgrade and rollback workflow presence exists, but no retained passed predecessor upgrade evidence; therefore first-release semantics apply.

## Complete migration graph and checksums

| Ordinal | ID | Dependency | SHA-256 |
|---|---|---|---|
| 0001 | `0001_product_foundation` | `- ` | `71d939094a97b4dd7c61de60542b60dd41cb238fd6bebfd75d53d723b00f3556` |
| 0002 | `0002_postgres_observability` | `0001_product_foundation ` | `c2098fa24ddae209fcf2ffeb369f7040d57018d58682a8513db9e943c749aa2d` |
| 0003 | `0003_incident_automation` | `0002_postgres_observability ` | `f1f250822f94c5cc95c0b8547402a7a1294a8a3f04f1b8bd6b2713a643712ee5` |
| 0004 | `0004_kafka_data_streams_monitoring` | `0003_incident_automation ` | `bf2a4cb663077d1df0be960300d04f4ad0ac2a43ab34fc0f01bf2fa40a1b32c6` |
| 0005 | `0005_console_foundation` | `0004_kafka_data_streams_monitoring ` | `3b6861df951b1e4c46d0c2b6430e9327c6cf83533a7c908e0dca1cdde7793197` |
| 0006 | `0006_pathway_asset_360` | `0005_console_foundation ` | `19dd1a7a5c6c36f3f807b13ca5d4785affc499cfbd53488c222b5a82b47faf10` |
| 0007 | `0007_automated_monitoring_data_products_rca` | `0006_pathway_asset_360 ` | `827dd6e892a7199d4b6e91577cc3108b10045a0d67fc68375b088d20e412213e` |
| 0008 | `0008_job_run_observability` | `0007_automated_monitoring_data_products_rca ` | `ce32e272e9e5f7b30387cfdffbe17a403ce22fd2cffc947aea41bcddcd3e0ffe` |
| 0009 | `0009_topic_queue_stream_360` | `0008_job_run_observability ` | `6568576cd65fbf0f151674322506c17d95d8b361370e5a74e9bd972937eb8e95` |
| 0010 | `0010_topic_queue_stream_360_completion` | `0009_topic_queue_stream_360 ` | `10230af88ce07b64b1e8d310065d2ae2461b4e09b8ef73c04fcf200a8f44d2cc` |
| 0011 | `0011_incident_automation_workbench` | `0010_topic_queue_stream_360_completion ` | `e5ac77c3fb833c9e8380922d2d38c5e23409f1446afe6b131a137d272b6ce1aa` |
| 0012 | `0012_incident_mapping_and_occ_fix` | `0011_incident_automation_workbench ` | `4ca3e9b2959b948c09879f125c5cd1de59b4b9c29df4e0f7e348c7a6316fa2b9` |
| 0013 | `0013_monitor_runtime_completion` | `0012_incident_mapping_and_occ_fix ` | `b8690cc9655a3992633ea57d07c9175dae90fb8dfbe602d3d4aea06155bdffef` |
| 0014 | `0014_data_product_360_completion` | `0013_monitor_runtime_completion ` | `7b0c111cff713342ebac7040a19a03399d9266f861749792269607b1842a7bc8` |
| 0015 | `0015_data_product_360_productization` | `0014_data_product_360_completion ` | `4bfd71dcd39336b0fcd0140589924d2f97635b90c9459f0fe5d3d6339a08155d` |
| 0016 | `0016_data_product_membership_dependency_runtime` | `0015_data_product_360_productization ` | `18ff89df0cac8777a3a72d076470a7a517b61d439e64b2b1287852a5f845178c` |
| 0017 | `0017_data_product_reconciliation_retry_date` | `0016_data_product_membership_dependency_runtime ` | `b34bc1859ee83a91f19bee1c96d67d1a20838149ee90dbedd56d376e0646c561` |
| 0018 | `0018_data_product_decision_reason_alias` | `0017_data_product_reconciliation_retry_date ` | `c01ff368f45722d80d7c5a920534e7f56fc2072831a12286a7a6a49a71eb4bb7` |
| 0019 | `0019_data_product_operation_claim_expires_date` | `0018_data_product_decision_reason_alias ` | `6ee0e71ae766305f526d7eaf91a594ae4fc8f6035ce4138b69cb618ac9912861` |
| 0020 | `0020_identity_rbac_tenant_bindings` | `0019_data_product_operation_claim_expires_date ` | `4b0505ec6d2e1f9db0edc19d6e7d808cff36ae2de3789dc921770b7ea3390d33` |
| 0021 | `0021_lineage_analysis_explorer` | `0020_identity_rbac_tenant_bindings ` | `48708bb08b183788d378f5666c19ab9d4294d073fca6df44ef1849b7af2bcd7e` |
| 0022 | `0022_aws_data_platform_collector` | `0021_lineage_analysis_explorer ` | `adb36e8f60ffe41e85bbc910de537a6b1b415da362a9b79eda6f13f69f9f50f8` |
| 0023 | `0023_stream_pathway_reliability_runtime` | `0022_aws_data_platform_collector ` | `04f5ec259ee4187c4ee423b0944d7b026e27f92f20755bb71330175bfec26149` |
| 0024 | `0024_job_run_reliability_runtime` | `0023_stream_pathway_reliability_runtime ` | `a3a7bcbd8594a51802a6c0e3f42a98c822b708e8ae7fa68bb664f96c5472666d` |
| 0025 | `0025_stream_pathway_reliability_production_closure` | `0024_job_run_reliability_runtime ` | `5d68f3c0acb2b265181276f3080f15d3acbf8abc39585b85715d9f5f6691fb30` |
| 0026 | `0026_stream_anomaly_retention_intelligence` | `0025_stream_pathway_reliability_production_closure ` | `dba7efc48003dc5877af8ac2f0e6949dd44878399e9cf3e2a77043f6d1009b44` |
| 0027 | `0027_platform_environment_tenant_multicluster_lifecycle` | `0026_stream_anomaly_retention_intelligence ` | `90b3c20f9ee44e5fa4a502e907fa3adcf3807a423ca42bad5071714d53476a25` |
| 0028 | `0028_pathway_investigation_history` | `0027_platform_environment_tenant_multicluster_lifecycle ` | `014f5406d0e063dfa1e1e51188e857028a28d6518d79a3a4907df783ea13d092` |
| 0029 | `0029_team2_data_intelligence_reconciliation` | `0028_pathway_investigation_history ` | `723551073408b65645be619083d8f85690d31c656239b9092ba94f3c64dd484a` |
| 0030 | `0030_team1_multi_broker_messaging_runtime` | `0029_team2_data_intelligence_reconciliation ` | `8b00435df096066438b8e582a71c7387147baae66be5b311102f02d70989cdb5` |
| 0031 | `0031_team3_post_incident_review_analytics` | `0030_team1_multi_broker_messaging_runtime ` | `95ebe301e7d43f7dc68668e0d8295654814c1bfe67e5d001a67d6dbb755c8f3b` |
| 0032 | `0032_team2_data_slo_production_runtime` | `0031_team3_post_incident_review_analytics ` | `46a6d4a721d81473fc5981116f6e54a6df5a55dcb62da0a17194df7d7cdfb8e1` |
