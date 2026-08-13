# Team 3 recurrence and similar incident intelligence v1 audit

## Baseline

Audited base SHA: `96d6e4f`. Latest merge at the audited head: PR #257. Starting terminal migration: `0031_team3_post_incident_review_analytics`. The checkout has no configured Git remote, so fetch and hosted PR discussion retrieval were unavailable; merged PR #259 was audited from commit `a52cbf3` and its repository audit.

| Capability | Existing | Durable | Production wired | Reusable | Gap |
|---|---|---:|---:|---:|---|
| Incident current projection | ES incident projection | yes | yes | yes | lacks normalized finding categories |
| Finding storage | current findings | yes | yes | yes | join/project features |
| Incident events | append-only timeline | yes | yes | yes | add human-decision event integration |
| Correlation features | finding/incident fields and separate engine | yes | yes | read only | historical projection |
| PIR analytics | PR #259 models/analytics | no | no | partial | service repository is in-memory |
| `recurrence_of` | strong Incident field | yes | yes | preserve | candidates need separate relationships |
| Root-cause candidates | Incident hypotheses | yes | yes | no | never authoritative |
| Confirmed PIR root cause | confirmed classification model | no | no | semantics only | production persistence/read boundary |
| Data Product associations | Incident IDs | yes | yes | yes | read public IDs only |
| Business service associations | Incident field | yes | yes | yes | normalize projection |
| Remediation outcomes | automation execution/verification | yes | yes | read only | bounded historical context projection |

Correlation groups active findings into one incident; flood control groups repeated signals within one incident. Neither is historical similarity or cross-incident recurrence. PR #259's PIR repository is explicitly `InMemoryPostIncidentRepository`; its domain semantics are reusable but its reviews and confirmed root causes are not durable production evidence.

No migration is added in this first functional-unvalidated slice. The existing incident read alias supports bounded candidate retrieval. Durable recurrence/family Elasticsearch resources and exact-head Elasticsearch/browser certification remain promotion gaps; released migration 0031 is unchanged.
