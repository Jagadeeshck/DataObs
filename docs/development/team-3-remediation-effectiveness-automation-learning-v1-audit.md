# Team 3 remediation effectiveness and automation learning v1 audit

Baseline: `39b7757` (locally available latest main snapshot); starting terminal migration: `0032_team2_data_slo_production_runtime`. GitHub review endpoints returned 404 in this checkout (no configured remote/authentication), so the supplied P1/P2 findings are the complete auditable input and external comment enumeration remains blocked.

| PR #263 finding | Severity | Reproduced | Root cause | Fix | Regression | Status |
|---|---|---:|---|---|---|---|
| Wrong incident read alias | P1 | Yes | Local stale literal | Reuse canonical repository constant | canonical-alias test | closed |
| Null categorical evidence matched | P1 | Yes | `str(None)` normalization | Drop null/blank before normalization | null test | closed |
| Unsupported same-asset recurrence | P1 | Yes | fallback taxonomy | Choose type only from matched evidence | recurrence suite | closed |
| Collection-order fingerprint instability | P2 | Yes | hashing trusted input order | sort/deduplicate/normalize at hash boundary | fingerprint test | closed |
| Candidate OCC metadata lost | P2 | Yes | `_source` returned alone | request and copy seq_no/primary_term | repository test | closed |
| Stale candidate retained | P2 | Yes | candidate writes were insert-only | refresh undecided changed proposals, preserve decisions | repository suite | closed |
| Reused/cross-scope score accepted | P1 | Yes | constructor lacked pair/scope/revision guards | fail-closed validation | recurrence suite | closed |
