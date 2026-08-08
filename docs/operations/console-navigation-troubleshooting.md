# Console navigation troubleshooting

1. Confirm `/api/v1/auth/me` returns trusted tenants, environments, permissions, and capability states. URL tenant/environment values are never authoritative.
2. Run `pnpm navigation:validate` for missing metadata, parent cycles, or detail-route leakage.
3. If a capability is absent, verify its backend permission. If shown as unavailable or not configured, inspect authenticated capability state.
4. After context switching, stale entity pages intentionally return to a safe capability parent and in-flight hook requests abort during cleanup.
5. Reset only `dataobs:shell:collapsed` to clear the persisted sidebar preference; do not store context or entity history there.
