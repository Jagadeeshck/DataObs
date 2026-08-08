# Operating the Azure Data Platform Collector

Install `requirements-azure-data-platform.txt` separately; core DataObs and other providers import without Azure packages. Configure the disabled synthetic example, select managed identity (preferred), workload identity, or referenced service-principal secret, and grant narrow read access. Validate before enabling. Secrets must use `env:` references.

Tune lookback, overlap, maximum runs, pages, observations, paths, depth, request timeout, and total integration deadline conservatively. Prefix collection remains opt-in. Failures use stable redacted codes and are isolated by service/resource family. Monitor partial/truncated evidence and checkpoint/evidence age; zero is emitted only after a complete measurement, while denial/truncation is missing or partial.

Rollback by disabling the integration and Azure role assignments. Retain generic append-only evidence and checkpoint/run audit state according to repository retention policy. There is no Azure migration to roll back.

Known limitations: Azure Public Cloud only; no broad discovery, mutations, SQL connection/query history, Spark sessions/logs, content reads, ACL inspection, lineage, quality, cost, or business-freshness claim. Team 0 must package optional dependencies, Team 2 owns canonical projection, and Team 5 owns onboarding UI. Live tests require `RUN_AZURE_INTEGRATION_TESTS=1` and approved synthetic resources; absence is a skip, not certification.
