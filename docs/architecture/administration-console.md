# Administration Console architecture

The authoritative manifest registers `/administration`, `/administration/my-access`, `/administration/access`, `/administration/access/new`, `/administration/access/:bindingId`, `/administration/audit`, `/administration/system`, and `/administration/preferences`. Every route has stable ownership, capability, permission, navigation/discovery metadata, breadcrumb/title metadata, a loading label, lazy loader, and (for binding detail) an encoded opaque parameter.

The capability-scoped client uses the shared authenticated and instrumented transport. Tenant/environment headers come only from trusted product context. React presents backend decisions; it does not calculate authority. Context changes abort inventory requests. Mutation success is shown only after a successful response.

Audit is an unavailable state because no read API exists. “Role grants” may only be derived from canonical role definitions; v1 does not claim effective-access evaluation. See [the audited contract](administration-access-contract.md).
