# Databricks collector service principal

Use a dedicated synthetic OAuth M2M service principal and environment-backed client ID/secret references. Grant workspace
access sufficient for approved read APIs only. For Unity Catalog grant `BROWSE`, `USE CATALOG`, `USE SCHEMA`, and only where
metadata APIs require it `SELECT`; grant `READ VOLUME` only for enabled volume metadata. Grant no ownership or writes.

Grant view access to selected warehouses and jobs (`CAN VIEW`). Grant `CAN USE` only on the system-table collector warehouse;
do not grant warehouse administration, job management, run-now, repair, cancellation, or output access. Grant explicit read
access only to `system.query.history` and `system.compute.warehouse_events`; a security administrator can expose a narrower
restricted dynamic view. Audit, billing, identity, access-history, lineage, notebook, file, and user tables are not required.
Permissions filter API results, so `browse_only` and incomplete visibility are expected.
