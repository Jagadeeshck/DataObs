# Operating the BigQuery warehouse collector

Install `requirements-bigquery.txt` as a Team 0 packaging choice; installations without it continue to load other providers and BigQuery reports `dependency_unavailable`. Copy the disabled synthetic example, retain explicit projects/locations, and prefer WIF via ADC outside Google Cloud. ADC and impersonation are constructed once per isolated execution. Legacy keys require both an opt-in flag and `env:` reference and are not recommended.

Tune lookback, overlap, row/page/resource/byte/time/concurrency and global observation limits conservatively. Job history needs regional visibility; denial produces partial evidence without blocking catalog families. Reservations are optional; none found is `not_configured`, not unhealthy. Troubleshoot using stable error codes only. Truncation is partial, delayed storage is stale/delayed source evidence, and metadata timestamps do not establish pipeline freshness.

Rollback by disabling the integration and stopping collection; retain generic observations, run evidence, and checkpoints for audit. No migration rollback is required. Live tests are opt-in with `RUN_BIGQUERY_INTEGRATION_TESTS=1` and require an approved synthetic project; a skip is not certification. Team 0 owns packaging, Team 2 owns canonical job/lineage projection, and Team 5 owns onboarding UI.
