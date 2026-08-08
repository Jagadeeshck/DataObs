# Trino collector least privilege

Use a dedicated non-impersonating service account. Metadata-only mode needs visibility only to approved catalogs, schemas, relations, and columns. Runtime-observation mode additionally needs read visibility for permitted `system.runtime` tables. Trino authorization depends on the deployed access-control plugin and connector, so validate effective visibility.

Do not grant writes, CREATE, INSERT, UPDATE, DELETE, DROP, CALL, kill-query administration, impersonation, or unrestricted catalogs. Never disable access controls or TLS verification. Basic passwords and JWTs use environment secret references; certificate/key and custom CA material use trusted file/environment references. Inline secrets, arbitrary headers, roles, session properties, extra credentials, and interactive authentication are rejected.
