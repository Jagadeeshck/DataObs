# SQL Server collector least privilege

## Metadata profile

Grant `CONNECT` to the configured database and narrowly scoped metadata visibility (`VIEW DEFINITION` at database or approved-schema scope as appropriate). Grant catalog `SELECT` only where the deployment requires it. SQL Server metadata is permission-filtered, so evidence states `visibility_scope = collector_principal`; absence is not proof that an object does not exist.

Never grant `sysadmin`, `securityadmin`, `serveradmin`, `db_owner`, or `CONTROL SERVER` for collection. SQL passwords and service-principal secrets must be DataObs secret references. Managed identity maps to `ActiveDirectoryMSI`; service principal maps to `ActiveDirectoryServicePrincipal`. Interactive, device-code, password-based Entra, default-chain, and unreviewed integrated authentication are forbidden.

## Freshness and profiling profile

Grant `SELECT` only on each explicitly approved relation. Policies expose aggregate results, never samples, values, predicates, definitions, SQL text, or rows.

## Optional storage statistics

Core metadata does not require DMV access. When storage statistics are enabled, SQL Server 2022+ may require `VIEW DATABASE PERFORMANCE STATE` and `VIEW SECURITY DEFINITION`; denial yields `storage_statistics_unavailable`, not an unhealthy provider. Review narrower metadata permissions, including `VIEW SECURITY DEFINITION` and `VIEW PERFORMANCE DEFINITION`, for the deployed version.
