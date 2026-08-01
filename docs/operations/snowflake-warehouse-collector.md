# Operating the Snowflake warehouse collector

Start from the disabled synthetic YAML. Configure a dedicated account, service user and read-only role, then provide
key material or OAuth only through a trusted secret reference. Workload identity must name AWS, AZURE, GCP or OIDC and
requires connector/runtime support. Never enable password, browser auth, custom hosts, TLS bypass or insecure OCSP.

Tune allowlists and hard catalog/history bounds before enabling. Account Usage delay means freshness can be stale even
after a successful run. Permission failure in a family is redacted and partial; unrelated families continue. Catalog
limits produce partial/truncated evidence rather than completeness. Troubleshoot stable codes, not connector text.

Rollback by disabling the integration and reverting provider composition; no migration rollback is needed. Connector
upgrades stay within the deliberate range and require dependency audit, mocked regression, SQL-template checks and an
opt-in sandbox run. Team 0 must package the optional connector. Hosted testing is disabled unless
`RUN_SNOWFLAKE_INTEGRATION_TESTS=1`; a skip is not certification.
