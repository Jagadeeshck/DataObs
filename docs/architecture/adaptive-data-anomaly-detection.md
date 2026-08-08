# Adaptive data anomaly detection

Adaptive detection is a policy of the canonical monitor runtime, not a scheduler or alert store. Supported bounded scalar families are freshness age, volume, null/unique rates, distinct count, numerical profiles, categorical profiles and generic scalar metrics. Explicit freshness SLOs remain authoritative.

Policies select static, adaptive or hybrid behavior. Hybrid clamps the adaptive range to absolute safety bounds. Baselines use deterministic MAD, IQR, 5th–95th quantiles or rolling median. Sensitivity maps to documented MAD-width multipliers: low 5.0, medium 3.5, high 2.5. Score is `min(100, normalized_deviation × 35)` and is distinct from confidence and finding severity.

Lifecycle states are collecting, ready, stale, degraded, resetting, disabled and error. Insufficient history is collecting—not healthy and not an active detector. Confidence is eligible samples divided by required samples, capped at one; seasonal fallback multiplies it by 0.75. Cohorts are capped at two dimensions. Unsupported or sparse cohorts fall back to the broader baseline with a reason.

Each immutable generation carries a deterministic ID derived from policy fingerprint, cohort and generation. Evaluations retain that ID, policy revision, method and cohort. Resets begin a generation; they do not delete observations. Persistent same-direction breaches are regime-change candidates sent to the existing human recommendation workflow, never silently accepted for critical monitors.
