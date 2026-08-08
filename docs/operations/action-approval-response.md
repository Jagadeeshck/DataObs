# Action approval response

Confirm tenant, environment, incident/target revisions, exact impact, risk, expiry, catalogue hash and separation-of-duty status. Reject if evidence is missing or the blast radius is unclear. Comments are bounded and must not contain credentials.

For conflicts, refresh instead of repeating a stale decision. For expiry, create a new preview and request. For `not_configured`, do not bypass the registry. After execution, distinguish queued, accepted, verification pending, verified execution, and recovery observed. Follow rollback guidance honestly; v1 does not promise automatic rollback.
