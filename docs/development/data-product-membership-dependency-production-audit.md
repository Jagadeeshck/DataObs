# Data Product membership and dependency production audit

> PR #119 supplied domain and in-memory foundations only. This PR is complete only when the same workflows operate through the production Elasticsearch repository, typed API, Product 360 Console, and retained certification evidence.

Release readiness remains **blocked**. A hosted workflow has not yet run; the table deliberately does not claim hosted evidence. No migration `0016` is required by the changes recorded here, and migrations `0001`–`0015` are not modified.

| Capability | PR #119 state | Production gap | Implementation | Test | Hosted evidence |
|---|---|---|---|---|---|
| idempotency Elasticsearch persistence | memory only | fixed-index persistence | Elasticsearch create/get/terminal transitions | unit and repository checks | pending |
| idempotency OCC | absent | concurrent terminal writes | sequence-number/primary-term update | repository checks | pending |
| completed-result replay | mutable current result | exact immutable snapshot | operation snapshot by recorded revision and ETag | lifecycle regression | pending |
| immutable result lookup | absent | production lookup | `get_product_revision` | lifecycle regression | pending |
| action-name normalization | mixed state/action names | canonical request identity | create/update/activate/deprecate/archive | lifecycle regression | pending |
| key expiry | model only | bounded query | scoped expiry listing without deletion | repository checks | pending |
| pending-operation repair | memory foundation | fencing/checkpoint implementation | not complete | pending | pending |
| operation listing | memory only | scoped ES query | bounded stable ES listing | repository checks | pending |
| revision listing | memory only | scoped ES query | bounded stable ES listing | repository checks | pending |
| signed product pagination | codec only | page metadata integration | not complete | pending | pending |
| signed revision pagination | codec only | API integration | repository accepts typed sort values | pending | pending |
| membership persistence | models only | ES implementation | not complete | pending | pending |
| manual membership | model only | service/API/UI | not complete | pending | pending |
| proposal generation | domain only | evidence adapter | not complete | pending | pending |
| proposal revisioning | model only | ES OCC | not complete | pending | pending |
| proposal acceptance | memory only | event-first ES workflow | not complete | pending | pending |
| proposal rejection | memory only | event-first ES workflow | not complete | pending | pending |
| membership exclusion | memory only | event-first ES workflow | not complete | pending | pending |
| decision audit | model only | immutable ES writes | not complete | pending | pending |
| signed membership/proposal/decision pagination | absent | end-to-end integration | not complete | pending | pending |
| dependency persistence | definition only | revisioned projection | typed projection model added; persistence incomplete | model checks | pending |
| dependency removals | absent | immutable removal evidence | not complete | pending | pending |
| cycle validation | domain traversal | production graph loading | bounded validator retained | unit | pending |
| direct traversal | helper only | ES projection query | not complete | pending | pending |
| transitive traversal | helper only | bounded production graph | not complete | unit helper | pending |
| graph truncation | helper only | API/UI propagation | typed graph model added | unit helper | pending |
| impact context | legacy model | dependency-focused partial result | typed summary model added | model checks | pending |
| API | lifecycle only | membership/dependency/revision routes | not complete | pending | pending |
| OpenAPI | lifecycle only | generated route surface | not complete | pending | pending |
| generated client | lifecycle only | generated route surface | not complete | pending | pending |
| Members tab | placeholder | API workflow | not complete | pending | pending |
| Lineage tab | placeholder | evidence states | not complete | pending | pending |
| Dependencies tab | placeholder | graph/table/editor | not complete | pending | pending |
| Revisions tab | placeholder | signed API page | not complete | pending | pending |
| Elasticsearch | partial repository | real 9.4.2 certification | core lifecycle persistence implemented | local unit only | pending |
| browser | absent | Playwright journey | not complete | pending | pending |
| axe | absent | accessibility journey | not complete | pending | pending |
| security | foundation | executable matrix | raw keys remain hashed; full matrix incomplete | unit | pending |
| hosted CI | absent | retained run and manifest | not available locally | not run | pending |

## Scope boundary

This work does not promote Data Product SLO, reliability, coverage, RCA, enterprise IAM, or remediation capabilities. The next milestone is **Data Product SLOs, reliability, and coverage**.
