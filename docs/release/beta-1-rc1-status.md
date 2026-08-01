# DataObs Beta 1 RC1 status

| Field | Result |
|---|---|
| Target SHA | Not selected; select one clean SHA after the main-integration repair is merged |
| Candidate version | 0.1.0-beta.1 |
| Certification date | Not certified; status refreshed 2026-08-01 |
| Terminal migration | 0023_stream_pathway_reliability_runtime (23 migrations) |
| Mandatory capability results | Not executed for one integrated final SHA |
| Optional capability results | AWS collector is implemented but excluded from the packaged Beta runtime until Collection Manager is packaged and live AWS evidence exists |
| Workflow run URLs | None retained for an integrated final SHA |
| Artifact IDs and names | Pending; each manifest capability must provide one exact-commit evidence artifact |
| Deployment / upgrade / rollback | Pending hosted execution |
| HA/restart | Pending hosted execution |
| Backup / restore | Pending destructive isolated-cluster execution |
| Security / browser / accessibility | Pending integrated hosted execution |
| Image build / scan | Pending integrated build, SBOM, provenance and vulnerability scan |
| Known limitations | Collection Manager is not a packaged workload; hosted exact-commit evidence is incomplete |
| Excluded components | Collection Manager, embedded Elasticsearch, Kibana, identity provider, demos and POCs |
| Publish status | not_published |
| Release decision | **NO_GO** |

No image, chart, tag, release, environment or registry object has been published. A GO decision requires one clean SHA reachable from `main`, successful mandatory capability workflows for that exact SHA, retained artifacts, independent verification, and explicit publication approval.
