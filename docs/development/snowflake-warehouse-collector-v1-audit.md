# Snowflake warehouse collector v1 audit

Audited base SHA: `5bd728f89efb49cea2e1c5d70640c1245761d7dc`. The terminal migration was derived with
`python scripts/release/current_terminal_migration.py` as `0023_stream_pathway_reliability_runtime`.

Reusable production code includes the Integration SDK registry, capability contract, trusted tenant context,
canonical resource IDs, redaction, retries and checkpoints; Collection Manager persistence/runtime; and the generic
provider resources established by 0022. AWS v2 supplied the per-execution factory and partial-family pattern.
PostgreSQL scanner code is production but profiling/lineage is outside this provider. AWS Lambda examples, POCs,
fixtures and Team 2 Airflow/Spark projection code were rejected. `services/scanner` is absent; scanner-worker is an
independent scheduler. No reusable identifier quoting utility existed, so this provider validates identifiers and uses
only fixed Account Usage templates.

The generic strict observation mapping stores bounded `source_evidence`, is provider-neutral, and checkpoint identity
supports provider/capability scope. Therefore no 0024 migration is justified. Connector imports are lazy and the
supported range is `snowflake-connector-python>=3.14,<5`; upgrades require unit/SQL-safety/dependency audit and an
opt-in hosted run. Authentication is non-interactive key pair, OAuth secret reference, or explicitly selected
AWS/Azure/GCP/OIDC workload identity when supported. Password, embedded tokens, browser auth, custom hosts and TLS/OCSP
overrides are rejected by the closed schema.

Scope is one configured account: identity, warehouses/resource monitors, bounded database/schema/table/view/external
table/column inventory, SQL-free query history, load, metering consumption and storage/metadata freshness. Account
Usage latency and permission gaps produce partial evidence. Team 0 owns packaging, Team 2 owns future reviewed lineage
projection/Access History parsing, and Team 5 owns onboarding UI. This slice is not hosted-certified or production-ready.
