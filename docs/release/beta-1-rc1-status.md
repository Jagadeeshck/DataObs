# DataObs Beta 1 RC1 status

| Field | Result |
|---|---|
| Target SHA | Not selected (PR #198 and origin/main verification blocked) |
| Candidate version | 0.1.0-beta.1 |
| Certification date | Not certified; audit updated 2026-08-01T20:20:58Z |
| Terminal migration | 0022_aws_data_platform_collector (22 migrations) |
| Mandatory capability results | Not executed; blocked |
| Optional capability results | AWS collector functional but excluded from packaged Beta runtime |
| Workflow run URLs | None |
| Artifact IDs and names | None; expected `dataobs-beta-1-rc1-integrated-certification` |
| Deployment / upgrade / rollback | Not executed |
| HA/restart | Not executed |
| Backup / restore | Not executed |
| Security / browser / accessibility | Not executed |
| Image build / scan | Not executed |
| Known limitations | Collection Manager is not a packaged workload; hosted exact-commit evidence unavailable |
| Excluded components | Collection Manager, embedded Elasticsearch, Kibana, identity provider, demos and POCs |
| Publish status | not_published |
| Release decision | **NO_GO** |

No image, chart, tag, release, environment, or registry object was published. A GO decision requires PR #198, no other mandatory open feature PRs, one clean SHA reachable from `origin/main`, and passing hosted evidence for every mandatory gate.
