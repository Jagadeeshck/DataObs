# Operating the Team 4 Oracle collector

Install `requirements-oracle.txt`; no Oracle Client is needed because python-oracledb Thin mode is used. Configure a direct host, port, and service name using the example. Production configuration requires TCPS and server hostname/DN verification. Secrets and wallet locations are references, never inline.

Enable freshness or profiling only per approved relation. Bounds and call timeouts limit work. A denied optional metadata family produces partial evidence while successful families remain usable. Checkpoint scopes are `identity`, `schemas`, `relations`, `columns`, `constraints`, `indexes`, `partitions`, `schema_snapshot`, `freshness/<relation>`, and `profiling/<relation>`; Collection Manager persists before OCC advancement.

Live suites are opt-in with `RUN_ORACLE_INTEGRATION_TESTS=1` and require approved disposable 26ai and 19c services. No live result is claimed by this change.
