# Trino SQL engine collector v1

Status: **functional_unvalidated**. Provider version `1` uses the official Python DBAPI client over verified HTTPS and direct protocol. It does not enable spooling or retrieve external segments. Fixed statements inspect only `information_schema`, `system.metadata`, and `system.runtime`.

| Trino server | Python client | status |
|---|---|---|
| 483 | 0.338.0 | expected (live test not run) |
| other releases | 0.338.x | unknown |

Runtime queries omit SQL, user, and source from projection; source is used only to exclude `dataobs-collector`. Runtime tasks are aggregated by query. History is labelled `bounded_runtime_history`; restart, eviction, delay, access control, and version differences cause gaps. A durable future path is a separately reviewed Trino event listener (HTTP/Kafka/OpenLineage), not this collector.

Unsupported: Presto, JDBC, profiling, custom SQL/assertions, row sampling, quality scans, complete query history, lineage, cost, logs, events, OAuth browser flow, Kerberos, and spooling.
