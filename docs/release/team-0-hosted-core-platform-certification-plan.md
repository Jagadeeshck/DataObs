# Team 0 hosted core platform certification execution plan

## Fixed policy and run identity

Run only through the protected `team-0-hosted-certification-test` environment.
The target must be a lowercase 40-character SHA reachable from the audited base
and `origin/main`. The target label is `dataobs-certification`; namespace/context
must contain `certification-test`; maximum duration is 480 minutes, nodes 6,
replicas 12, tenants 3, load concurrency 50, generated documents 100,000, and TTL
12 hours. `cleanup_confirmation` must be `DELETE_RUN_OWNED_RESOURCES`. Missing
protected prerequisites produce `PENDING`; they never produce pass evidence.

Every report binds target SHA, workflow/run attempt, terminal migration, producer,
timestamps and safe tool versions. Tokens and secrets are never artifacts. The
consolidated artifact name is
`team-0-hosted-core-platform-certification-v1-evidence`.

## Phases

In the table, **owner** is the accountable Team 0 function. **Result** is the
initial state in this checkout and is updated only in retained run artifacts.

| # / phase | Prerequisite | Command / workflow | Expected evidence | Pass / fail criteria | Cleanup | Owner | Result |
|---|---|---|---|---|---|---|---|
| 1 Environment preparation | protected driver, exact SHA, approved quotas | hosted workflow `validate`/`provision` | `environment-report.json` | disposable context, labels, TTL and limits match / any production/shared target or missing input | delete run-owned infra | Platform | PENDING |
| 2 Secured Elasticsearch | disposable ES 9.4.2 secret refs and CA | protected dependency driver | `elasticsearch-report.json` | authenticated TLS verification, security on, healthy nodes/shards / anonymous, plaintext, wrong version | delete only run-owned ES resources | Platform/Security | PENDING |
| 3 Disposable OIDC | protected issuer/client/users | protected OIDC driver | `oidc-report.json` | code+PKCE S256, issuer/audience/signature/expiry checks / bypass or shared-token auth | remove run client/users | Security | PENDING |
| 4 Kubernetes deployment | safe context and dependencies | `helm upgrade --install` through driver | `kubernetes-report.json` | all owned resources ready in test namespace / unsafe context or unavailable workloads | uninstall run release | Platform | PENDING |
| 5 Production Helm validation | exact candidate images and secret refs | `helm lint`, template, chart assertions | `helm-report.json`, manifest SHA-256 | production security/external dependency contracts pass / shortcut, mutable/unpinned input, mismatch | securely remove rendered file | Platform | PENDING |
| 6 Migration application | reachable secured ES | migration job; doctor, status, repeat apply | `migration-report.json` | expected/applied terminal and checksums match, repeat safe, ready / drift or failure | retain DB for later phases | Release | PENDING |
| 7 Security validation | live OIDC/API | existing IAM/security and privileged-access suites | `authentication-report.json`, `authorization-report.json`, `privileged-access-report.json` | all valid/invalid, RBAC, strong-auth, approval/revoke/expiry cases pass closed / any fail-open | revoke grants | Security | PENDING |
| 8 Multi-tenant seed | migrations ready | protected synthetic seed driver | `tenant-isolation-report.json`, fixture fingerprints | exactly A/B/C with distinct users/roles/environments and bounded fixtures / customer data or isolation leak | mark fixture resources run-owned | Security/Platform | PENDING |
| 9 Core capability smoke | seeded tenants | bounded existing certification clients | `capability-smoke-report.json` | selected lineage/monitor/quality/stream/incident/job/search journeys pass / integration failure (cross-team failures separate) | remove ephemeral requests | Platform | PENDING |
| 10 Scale/HA | stable baseline | existing production scale/HA workflow/harness | referenced scale evidence + checksum | selected topology scenarios pass validator at exact SHA / pending/failed scenario or topology overclaim | remove load generators | Platform | PENDING |
| 11 Dependency resilience | stable workload | existing DR/dependency harness | referenced resilience evidence + checksum | ES latency/outage/429, OIDC/JWKS, OTLP and recovery meet matrix / fail-open, storm, loss, non-recovery | revert every fault | Platform/Security | PENDING |
| 12 Upgrade | actual retained release | resilience `upgrade` phase | `upgrade-report.json` | prior release deployed/seeded then target migrates and preserves data/IAM/workers / invented source, loss or unrecovered disruption | retain target | Release | PENDING |
| 13 Rollback | compatibility metadata | resilience `rollback` phase | `rollback-report.json` | safe rollback verified, or tooling proves `rollback_blocked_by_migration` / destructive reversal or unguarded rollback | return target app | Release | PENDING |
| 14 Backup | disposable snapshot repo | `backup_dataobs.py` via protected driver | `backup-report.json` | manifest-scoped successful snapshot, zero failed shards / wildcard, unrelated scope or failure | retain snapshot for restore | Platform | PENDING |
| 15 Destructive restore | opt-in and resource manifest | resilience `destructive-restore` phase | `restore-report.json` | only registered resources removed/absent/restored; fingerprints, IAM, lifecycle, migrations match / unrelated deletion or mismatch | retain restored test state | Platform/Security | PENDING |
| 16 Recovery verification | restored state | recovery measurement + smoke | `recovery-report.json` | ready and verified; observed recovery/data-loss windows derived from timestamps / invented target or incomplete recovery | stop writers | Platform | PENDING |
| 17 Evidence consolidation | all mandatory producer outputs | consolidation phase | manifest, reports, `checksums.sha256`, tool versions | one exact SHA/run/attempt/migration; every mandatory reference present / mixed, stale or missing evidence | none | Release | PENDING |
| 18 Independent verification | immutable downloaded bundle | existing independent validators + redaction scan | `hosted-core-platform-verification.json` | checksums, identity, topology and scenarios pass; no leak / producer-only, mismatch, pending, leak | quarantine failed bundle | Release/Security | PENDING |
| 19 Support-matrix decision | verified bundle | existing support evaluation/release tooling | `support-matrix-decision.json` | `supported` only with every mandatory field; otherwise truthful unvalidated/failed / unsupported claim | no repository mutation by run | Release | PENDING |
| 20 Release decision | verification and support decision | existing release authority, dry run | `release-decision.json` | evidence-derived allowed state, never publication / publication or bypass | none | Release | PENDING |
| 21 Cleanup | run ownership inventory | cleanup phase (`if: always()`) | `cleanup-report.json` | namespaces/workloads/users/OIDC/ES/load/snapshot/cloud run-owned resources absent; shared services untouched / assumed or incomplete cleanup | retry/escalate until TTL owner confirms | Platform | PENDING |

## Required security and operations assertions

Authentication covers valid sign-in, expiry, issuer, audience, signature, missing,
malformed and unsupported methods. Authorization covers platform admin, tenant
admin, operator, viewer and supported service principal; A↔B access and wrong
environment must be denied. Privileged access covers self/duplicate/expired
approval, scope, strong auth, revoke/expiry and audit. Credential lifecycle uses
disposable values through staged, pending, verified, promoted, retired and safe
rollback states.

Healthy `/livez`, `/startupz`, `/readyz` are captured. During Elasticsearch
outage liveness remains independent while readiness fails, calls are bounded,
workers back off, and detection/recovery times are measured. OIDC never fails
open. OTLP failure does not stop product/workers and its queue/memory remain
bounded. Platform operations captures health, components, workers, migrations,
backups, release, SLO/error budgets, environments, clusters/installations/fleet,
drift and capacity; absent evidence is `unknown`, `unvalidated` or
`insufficient_data`, never healthy.

Support-bundle and all-log scans detect Authorization/Bearer, JWT-like strings,
password/client-secret/cloud-key/private-key patterns and credential-bearing
URLs. Findings expose only file, rule, severity and a safe SHA-256 fingerprint.
The verifier rejects any finding, wrong SHA/migration/workflow/attempt, stale or
missing file, checksum mismatch, failed/pending mandatory scenario, or topology
overclaim.
