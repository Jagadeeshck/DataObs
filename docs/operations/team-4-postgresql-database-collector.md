# Operating the PostgreSQL Database Collector

Start from `config/integrations/postgres-database.example.yaml`, keep it disabled, supply only secret references, validate configuration, test the connection, then run one-shot collection. Production defaults to `verify-full`; `verify-ca` is an explicit weaker hostname-verification tradeoff. `disable`, `allow`, `prefer`, and `require` are rejected by the new provider. Monitor bounded statement timeouts, truncations, partial failures, evidence age and generic checkpoint age using low-cardinality provider/capability/family/status/error/resource-type labels only.

Psycopg `3.3.4` is the locally resolved package-index baseline and the declared range is `>=3.3.4,<3.4`. Opt-in live CI uses synthetic data and `RUN_POSTGRES_INTEGRATION_TESTS=1`.

| PostgreSQL | Psycopg | Status |
|---|---|---|
| 18.x | 3.3.4 | live workflow target; unvalidated locally |
| 17.x | 3.3.4 | live workflow target; unvalidated locally |
| 16.x | 3.3.4 | live workflow target; unvalidated locally |
| 15.x | 3.3.4 | expected, not tested |
| 14.x | 3.3.4 | expected, not tested |
| 19 beta | n/a | unsupported for certification |
