# Trusted tenant enforcement

`X-DataObs-Tenant` and `X-DataObs-Environment` are selectors, never credentials. The API normalises the configured `dataobs_access` claim into tenant/environment pairs and rejects malformed, unknown, unauthorised, or ambiguous selections. Repository queries must filter and writes must stamp the resolved context; IDs and cursors remain tenant/environment bound.
