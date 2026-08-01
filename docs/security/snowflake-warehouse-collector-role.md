# Least-privilege Snowflake collector role

Use a dedicated service user and role; never use `ACCOUNTADMIN` at runtime. Inventory-only visibility should grant only
warehouse monitoring plus usage on explicitly allowlisted databases/schemas. Operational history may additionally use
`MONITOR USAGE` and `IMPORTED PRIVILEGES` on `SNOWFLAKE` for Account Usage. Do not grant ownership, writes, table
`SELECT`, future grants, user/role administration, or notification-user visibility. Table SELECT requires separate
future profiling approval.

Synthetic starting point (security administrators should tailor and review it):

```sql
CREATE ROLE DATAOBS_SYNTHETIC_READER;
GRANT MONITOR USAGE ON ACCOUNT TO ROLE DATAOBS_SYNTHETIC_READER;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE DATAOBS_SYNTHETIC_READER;
GRANT USAGE ON DATABASE SYNTHETIC_ANALYTICS TO ROLE DATAOBS_SYNTHETIC_READER;
GRANT USAGE ON SCHEMA SYNTHETIC_ANALYTICS.SYNTHETIC_CURATED TO ROLE DATAOBS_SYNTHETIC_READER;
```

Inventory-only deployments can omit Account Usage operational grants where their chosen safe metadata sources permit.
Optional visibility must remain restricted to configured databases/schemas. Key rotation and secret backend access are
managed outside DataObs; evidence never stores private keys, passphrases or OAuth tokens.
