---
name: elasticsearch-migrations
description: Build and validate strict Elasticsearch mappings, idempotent forward migrations and version compatibility.
---
# Elasticsearch Migrations

1. Inspect current migration registry, terminal identity and released checksums.
2. Confirm configured Elasticsearch server and python client versions; currently v1.0.0 docs target ES 9.5.5 but old CI/docs may target 9.4.2.
3. Reproduce first apply, repeated apply, existing-index compatibility and alias/reindex behavior against disposable real Elasticsearch.
4. Never edit a released migration/checksum or loosen strict mappings. Create a new forward-only migration with migration and rollback/restore plan.
5. Test tenant scoping, writer-owned field definitions, mapping semantics, 0/missing/stale states and historical data.
6. Retain exact-SHA JUnit/evidence and independently verify.
**Output:** migration rationale, immutable checksum proof and real-stack compatibility report.

**Always:** respect `.kiro/steering/safety-and-evidence.md` and the canonical team ownership map. Use real source, current main and exact-SHA proof.
