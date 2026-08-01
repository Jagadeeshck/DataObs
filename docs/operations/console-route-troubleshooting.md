# Console route troubleshooting

1. Find the exact path in `src/app/routes.ts`; duplicate IDs/paths and wildcards
   are invalid.
2. Confirm its loader key exists in `src/app/App.tsx` and run `pnpm test`.
3. Check the trusted identity permission independently from tenant capability
   status. A bundle loading successfully proves neither configuration nor API
   health.
4. For a disabled entry, inspect the capability value returned by
   `/api/v1/auth/me`; missing is unknown, `not_configured` needs onboarding, and
   `unavailable` needs service diagnostics.
5. For import failure, use **Retry page** or return to Command Center. The shell
   context is intentionally retained and raw exception payloads are hidden.
6. For dynamic links, use `entityLink`; never concatenate identifiers.

After a deployment rollback, clear only the service-worker/CDN asset cache (if
one is configured). Do not clear OIDC/session state or weaken permissions to
recover a route.
