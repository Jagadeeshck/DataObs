# Break Glass Access

## Preconditions
Valid OIDC authentication, healthy append-only audit persistence, synthetic/disposable rehearsal scope, current ETag, incident/change reference, and confirmed tenant/environment.

## Required permission
`break_glass:request / approve / activate`.

## Required approval
A distinct authorized approver; two for policy-classified critical operations. The requester never self-approves.

## Safety checks and scope confirmation
Confirm exact principal, tenant, environment, allowlisted operation, expiry, current version, rollback material and request ID. Stop when evidence is missing.

## Evidence capture
Capture metadata-only plan IDs, revisions, outcomes, timestamps, workflow SHA and redacted verification results. Never capture secret values or raw claims.

## Execution
request, approve, and activate a scoped grant. Use OCC and do not retry an ambiguous destructive result automatically.

## Verification
Verify readiness, intended authorization, audit append, expiry/revocation, and that unrelated tenant/environment access remains denied. Hosted evidence is pending until the exact-SHA workflow succeeds.

## Rollback
revoke the grant. Re-verify readiness and append rollback evidence.

## Revocation or retirement
Revoke temporary authority immediately; retire old credentials only after overlap and verification evidence.

## Post-event review
Record outcome, deviations, remaining exposure and follow-ups, then close immutable terminal state.

## Escalation
Escalate to Team 0 security/release authority and the external identity/secret provider owner. Treat audit failure as a stop condition.

## Prohibited actions
No password backdoor, local superuser, OIDC/JWT/tenant/route-policy bypass, wildcard scope, self-approval, secret logging, arbitrary shell/SQL, audit disablement, or production game-day execution.
