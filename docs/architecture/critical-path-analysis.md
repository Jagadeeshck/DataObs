# Critical-path analysis

Run critical path uses longest-path analysis over observed task dependencies, falling back to stage evidence when tasks are unavailable. Parallel branches are evaluated independently. Cycles, unknown dependencies, absent/negative timestamps, and incomplete graphs reduce confidence and are disclosed in `missing_evidence`.

Segments separate waiting and execution time, identify blockers and retain an evidence reference. Retries are separate observed entities; skipped work contributes zero execution time. Clock-skew-derived negative durations are clamped to zero and cannot produce high confidence.
