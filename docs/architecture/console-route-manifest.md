# Console route manifest

`ui/dataobs-console/src/app/routes.ts` is the authoritative inventory for all
authenticated product routes. Each entry owns its stable ID/path, labels,
navigation group/icon, team, implementation state, UX permission, visibility,
parent breadcrumb, dynamic label, document title, suspense label, and loader
key. `App.tsx` renders that list and its typed loader map; consistency tests fail
for an unimplemented loader, duplicate path/ID, wildcard Quality route, or
unregistered implementation.

Authentication paths remain explicit and outside `AppShell`. Unknown paths use
the accessible not-found route. Static implementation state, trusted identity
permissions, and `/api/v1/auth/me` tenant capability state remain separate.
Missing runtime capability state is `unknown`, never inferred as healthy from a
successful code import. Frontend permission handling is UX-only; APIs remain
authoritative.

Dynamic breadcrumbs are built from `parentId` and decoded route parameters.
Malformed encodings do not match. Titles use `DataObs — <capability> <safe id>`
and fall back to the static capability label until an identifier is available.

Rollback is a single revert of the manifest-driven router. Do not restore a
parallel feature wildcard: add one manifest record and loader instead.
