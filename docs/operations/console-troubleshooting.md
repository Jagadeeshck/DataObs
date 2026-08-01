# Console troubleshooting

Use the response `X-Request-ID` to correlate browser failures with API and Elasticsearch logs. An incomplete source is rendered as partial/unknown, not zero. Check `/healthz`, API `/health`, migration status, then tenant and environment membership.
# Console product experience troubleshooting

If startup reports **Console unavailable**, verify same-origin `/api/v1/auth/me`, the OIDC session and membership payload. Access denied means no trusted tenant/environment membership was supplied. Do not work around either state with a caller-entered tenant header.

Partial and unavailable banners preserve usable capability evidence. Capture the displayed request ID, tenant/environment names (not tokens), route and UTC time. A topology truncation banner requires narrower filters, not a larger browser query. An unavailable Integrations page means Team 4 metadata is absent; production intentionally has no fixture fallback.
