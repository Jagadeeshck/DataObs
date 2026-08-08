# Service principals

Service-principal records are metadata only. Supported authentication is federated/workload OIDC, short-lived externally managed credentials, or exceptional externally managed API keys. Password and browser authentication are unsupported. Registration, owner/scope change, suspension, approved reactivation, rotation recording and revocation require tenant/environment enforcement, OCC, idempotency and audit. No API may generate a long-lived secret or disclose external identity existence. Durable APIs remain pending.
