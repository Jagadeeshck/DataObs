# Operating the Team 4 MariaDB collector

Install `requirements-mariadb.txt` only on MariaDB workers and ensure the MariaDB Connector/C native library used by Connector/Python is supported. Configure a dedicated least-privilege account, explicit host/port/database, an indirect password reference, and a trusted CA file. Inline passwords and credential-bearing DSNs are rejected.

The certified targets are MariaDB 11.8 LTS (primary) and 11.4 LTS (secondary). A MySQL server fails with `server_product_mismatch`; a missing Python/native connector fails with `dependency_unavailable`. Core health never depends on `userstat` or Performance Schema. Freshness is explicit timestamp-column MAX only; aggregate profiling is disabled by default.

Run live disposable-server tests with `RUN_MARIADB_INTEGRATION_TESTS=1`. Until hosted exact-commit and live results are independently verified, status remains `functional_unvalidated` and production readiness is not claimed.
