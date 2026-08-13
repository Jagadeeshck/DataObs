# Version upgrade Console architecture

The route `/administration/platform/upgrades` is a contextual child of Platform Operations and requires `platform_operations:read`. It independently settles two bounded GET requests: compatibility and upgrade readiness. Requests are deduplicated, abortable, timeout-bounded, and manually refreshed. No POST, PATCH, DELETE, deployment transition, Helm, Terraform, Kubernetes, migration apply, or rollback endpoint is called.

The page is an evidence presentation layer. Team 0 owns version comparison, support policy, readiness, rollback and migration decisions. Missing contract fields remain visibly unknown. Compatibility, upgrade readiness, operational readiness, release decision and certification are independent claims.
