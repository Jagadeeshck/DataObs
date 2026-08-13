# Platform supportability Console troubleshooting

1. Confirm the operator has `platform_operations:read`.
2. Use **Refresh evidence** once; the page intentionally does not poll rapidly.
3. A partial-evidence alert lists only the failed section category. Successful sections remain usable.
4. Confirm `/api/v1/platform/{section}` responses and server-side audit events using approved operational tooling.
5. Do not paste response bodies, configuration fingerprints, credentials, tokens, private endpoints or diagnostic text into telemetry or tickets.

The Console cannot restart, deploy, restore, migrate, rotate secrets or generate a support bundle. Follow Team 0 governed workflows for those operations.
