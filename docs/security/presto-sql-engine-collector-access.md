# Presto collector access

Create a dedicated Presto service identity. Grant visibility only to approved catalogs, approved schemas, and metadata. Runtime mode additionally requires read visibility for `system.runtime.nodes`, `system.runtime.queries`, and `system.runtime.tasks`.

Do not grant writes, CREATE, INSERT, UPDATE, DELETE, MERGE, DROP, CALL, query-kill procedures, impersonation, or unrestricted administration. The collector cannot issue arbitrary SQL and never queries business relations. Exact enforcement depends on Presto system access control, each catalog connector, and its underlying source.

Only Basic/LDAP-style password authentication is supported in v1, over verified HTTPS with an environment secret reference. Kerberos is planned v2; JWT, OAuth2, client certificates, interactive login, and unauthenticated production use are deferred.
