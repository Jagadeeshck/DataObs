# Certification and release gap audit

Audit date: 2026-07-27. Audited merge range: PR #171 through PR #173 at
`6e2f86e`. This checkout has no configured Git remote or authenticated GitHub
CLI, so hosted run, artifact, issue, and pull-request dispositions remain
pending external execution. No capability is promoted by this audit.

| Area | Intended result | Current result | Gap | Required fix |
| --- | --- | --- | --- | --- |
| Capability ledger | Claims follow retained final-SHA evidence | Hosted dimensions remain missing | Final-head artifacts unavailable | Preserve pending states until hosted verification |
| Current baseline | Honest product snapshot | Records non-production blockers | Final PR run IDs unavailable | Update only after hosted runs |
| Evidence index | Retained artifacts and producer SHA | Definitions are indexed, executions are not | No final-head artifact IDs | Run and independently verify hosted producers |
| Issue closure report | Evidence-based issue disposition | #25 is correctly recorded pending | GitHub state cannot be changed here | Reopen pending proof; close completed only after proof |
| Data Product certification | Exact-SHA real Elasticsearch evidence | PR workflows existed; main merge SHA was not certified | A tag could not match PR-head evidence | Certify PR heads and pushes to `main` |
| Signal-path certification | Redacted retained end-to-end evidence | Workflow definition exists | Final-head hosted execution pending | Retain and verify `e2e-signal-path` |
| Release gate | Exact, successful, unambiguous workflow runs | Untested `gh api -f` call could select an arbitrary success | Implicit POST/API ambiguity and no duplicate rejection | Use tested GET verifier and record IDs/URLs |
| Release image scanning | Scan before supported tags exist | Images were pushed before Trivy ran | Failed candidates remained published | Build locally, SBOM and scan, then authenticate and push |
| Elasticsearch split | Stable explicit compatibility surface | PR #173 removed wildcard export | Base module omitted from focused mypy gates | Type-check wrapper and base in all Python gates |
| Stale PR and issue | #162 closed; #25 evidence-based | Repository report says both actions pending | No authenticated GitHub access | Perform cleanup after final hosted proof |

## Elasticsearch repository ownership

`elasticsearch_repository_base.py` owns the complete persistence implementation.
`elasticsearch_repository.py` is the supported import path and owns only the
precision-safe reconciliation overrides plus an intentional `__all__`
compatibility contract. The wrapper must not re-export helper modules or
implementation-only types. Contract and Elasticsearch 9.4.2 integration tests
protect method availability, microsecond eligibility and claim boundaries,
deterministic `search_after`, mapped event ordering, immediate dependency
visibility, and tenant/environment scoping.

## Migration audit

The immutable released registry remains `0001_product_foundation` through
`0019_data_product_operation_claim_expires_date`. This change introduces no
migration and does not edit persisted Elasticsearch data. The checksum gate must
be run against `origin/main` in hosted CI; it cannot be represented as hosted
proof by a local run.

## Remaining blockers

OIDC/RBAC, trusted tenant resolution, HA, backup/restore, and full deployment
hardening remain explicitly out of scope and block production readiness.
