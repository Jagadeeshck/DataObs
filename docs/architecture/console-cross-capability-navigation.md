# Console cross-capability navigation

The typed registry in `ui/dataobs-console/src/app/routes.ts` is authoritative for rendered routes, navigation, breadcrumbs, permissions, support/configuration state, safe entity parameters, Quick Find eligibility, ownership, and lazy loaders. `App.tsx` generates protected and public route elements from it. Groups are Overview, Observe, Respond, Configure, and non-navigation System. Unauthorised permission-sensitive entries are omitted; unavailable entries are visible only as disabled explanations.

Each detail route has one parent and uses `encodeURIComponent` through `buildRoutePath`. Existing external paths are unchanged. Breadcrumbs derive parents from registry IDs and use safe route names; capability pages may later supply non-sensitive entity display names. Navigation state meanings are available, preview, not configured, unavailable, and planned—none means healthy.
