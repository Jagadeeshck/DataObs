# Event Storm runtime

Event Storms are durable flood windows associated with correlation groups. `evaluate_flood` deep-copies input and returns `(decision, updated_window)`. Event IDs are deterministic; retained events, samples and explanations are bounded. Event time drives the watermark and observation window. Late/replayed events have deterministic outcomes and do not increment suppression twice.

States are `normal`, `elevated`, `flooding`, `recovering` and `closed`. Recovery is threshold-driven, hysteresis explicitly holds recovery, and closure requires explicit quiet-time evaluation. Critical severity, data/retention risk, new critical product/service, expanded asset or scope, new failure family, business impact and invalid representative signals generate exact bypass reason codes. Bypass creates escalation intent without incrementing suppression.

Flood projections use the released strict suppression index; transitions and provider-neutral notification decisions use the append-only suppression stream. Notification actions (`notify`, `coalesce`, `escalate`, `summary_due`, `hold_recovery`) describe eligibility only, never delivery.
