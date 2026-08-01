# Console product experience

The typed registry in `src/app/routes.ts` is the source for product navigation, permissions, ownership, availability and breadcrumbs. Feature routes continue to render their capability-owned implementations. Unknown paths and route exceptions have accessible recovery pages.

The shell establishes a trusted `/api/v1/auth/me` context before rendering product data. Tenant choices are limited to authenticated memberships; changing tenant or environment increments a refresh generation and abortable page hooks discard previous-context requests. The URL contains only safe tenant/environment, time-range and filter identifiers. Tokens remain in OIDC session storage; secrets are never product preferences.

Evidence states are healthy, warning, critical, unknown, not configured, unavailable, stale and partial. Zero is rendered when measured; absent values render Unknown. Pages disclose observation time, coverage, missing inputs, request identifiers and truncation when contracts supply them. Missing evidence cannot derive healthy state.

Command Center consumes the canonical bounded `/api/v1/command-center` projection with explicit start/end. Data Flow consumes `/api/v1/topology` at server-enforced limits of 1,000 nodes and 2,500 edges. Neither production route imports fixtures. Integration metadata is expected at `/api/v1/integrations/metadata`; absence is explicit and never invokes a production fallback.
