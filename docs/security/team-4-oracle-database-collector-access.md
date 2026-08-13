# Oracle collector least privilege

Grant connection permission (`CREATE SESSION`) and access only to required objects. Accessible `ALL_*` views naturally scope metadata to the collector principal; do not grant DBA, SYSDBA, `SELECT_CATALOG_ROLE`, `SELECT ANY DICTIONARY`, or blanket `SELECT ANY TABLE`. Grant SELECT on individual business relations only when their aggregate freshness/profiling policy is approved.

The v1 authentication mode is password by secret reference and always normal authorization. Privileged modes, arbitrary descriptors/Easy Connect strings, session initialization, PL/SQL, and inline wallet material are rejected. TCPS with certificate and hostname/DN matching is mandatory.
