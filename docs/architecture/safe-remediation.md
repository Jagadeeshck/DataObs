# Safe remediation

DataObs v1 provides a deny-by-default control plane, not autonomous remediation. See [control-plane architecture](safe-remediation-control-plane.md), [approval runtime](action-approval-runtime.md), and [verification semantics](action-verification.md).

The catalogue recognizes bounded scan rerun, freshness recheck and connection test actions, but the audited baseline exposes no certified public service contract, so they truthfully remain `not_configured`. Notification suppression is preview-only. No destructive or generic executor is available.
