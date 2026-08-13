# Team 0 → Team 5 security posture handoff

Team 5 may display only the privileged `GET /api/v1/platform/security` summary: posture state, control category counts, evidence state/freshness, blocker count, remediation code, critical finding count, active exception count, and release security gate. Require `platform_operations:read` through the canonical route policy.

Do not build a vulnerability browser from this contract. Detailed findings, CVE/component data, infrastructure identifiers, evidence source locations, exceptions, or secrets remain server-side and restricted. Unknown, stale, missing, and unvalidated states must be visually distinct and must never render as PASS. No percentage score or certification language is permitted.
