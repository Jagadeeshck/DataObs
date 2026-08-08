# SQL engine collector foundation

`integrations/sql_engine` is Integration SDK production code: typed engine/connection contracts, strict identifier quoting, a closed statement registry, bounded `fetchmany()` execution, cancellation, and partial-failure contracts. It intentionally has no arbitrary-SQL API and is not a provider. PostgreSQL remains on Scanner Worker; consolidation requires a separate compatibility-tested change.

Trino and PrestoDB are separate provider identities and dialect packages over this foundation. Shared validation prohibits mutations, calls, session/authorization changes, transactions, passthrough functions, kill procedures, comments, multiple statements, and `SELECT *`; providers may strengthen but never weaken it.

## SQL Engine Aggregate Profiling v2 (deferred)

Any future profiling must be explicit opt-in, connector-aware, restricted to approved table allowlists, and enforce scan-cost plus available row/byte limits. V1 performs no aggregates over business relations.
