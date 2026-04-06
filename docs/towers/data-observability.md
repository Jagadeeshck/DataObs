# Data Observability Tower

The Data Observability tower ensures trust in analytical and operational data.

## Core controls
- **Freshness:** detect stale datasets by comparing latest update timestamp against SLA.
- **Validation:** apply reusable checks (null, uniqueness, value range, referential integrity, row counts).
- **Schema monitoring:** detect breaking schema changes.
- **Lineage:** map upstream/downstream dependencies for blast-radius analysis.

## Suggested rollout
1. Tier-1 datasets first (financial and customer-facing metrics).
2. Define data contract SLAs (freshness and completeness).
3. Enable automatic incidenting for critical failures.
4. Expand checks to tier-2/3 and self-service domains.
