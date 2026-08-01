# Console investigation context

`investigation.ts` defines a URL-backed, non-sensitive handoff containing source route, entity type/ID, time range, overlay, tab, filter summary, and safe return route. Values are capped and entity parameters are encoded. Return routes must begin with one slash, remain same-origin, and match the registry. Missing or rejected context never blocks direct links.

Context carries no evidence, secrets, credentials, comments, or arbitrary URL. Tenant and environment remain controlled by trusted product context rather than handoff parameters. Canonical target IDs cover Incident Workbench, Monitor/Run/stream/connector/schema/pathway/product details and can be adopted by capability owners without another persistence layer.
