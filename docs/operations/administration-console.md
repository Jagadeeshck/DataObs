# Operating the Administration Console

Use **My access** to inspect the trusted principal and scope. Users with `iam:read` can inspect tenant-bounded bindings; `iam:write` is required for create and revoke. Creation is review-first and offers canonical roles and trusted scope only. Revocation requires explicit confirmation and is never automatically retried.

If data is unavailable, retain the displayed request ID for support. Do not paste tokens, cookies, raw claims, or identity-provider secrets into tickets. Roll back by reverting the Console commit; no migration, backend IAM rule, or stored security document is changed by this milestone.
