# Global entity search v1 contract audit

Audited base: `c5b7dff6573b6fd0ce76122e7112b726c35d431d` (includes PRs 214–218). The checkout has no configured remote, so open PR inspection was unavailable.

| Entity                    | Owner  | Canonical route    | API/filter                                                | Bound                                                         | Permission           | v1  |
| ------------------------- | ------ | ------------------ | --------------------------------------------------------- | ------------------------------------------------------------- | -------------------- | --- |
| Asset                     | Team 2 | `asset-360`        | `GET /api/v1/assets`, `search`, limit 50, cursor          | Server search; first page only                                | `assets:read`        | Yes |
| Data product              | Team 2 | `data-product-360` | `GET /api/v1/data-products`, `search`, limit 5, cursor    | Server search                                                 | `data_products:read` | Yes |
| Monitor                   | Team 4 | `monitor-360`      | `GET /api/v1/quality/monitors`, `search`, limit 5, cursor | Server search                                                 | `quality:read`       | Yes |
| Job                       | Team 2 | `job-360`          | `GET /api/v1/jobs`, `search`                              | Response bound is not explicit                                | `console:read`       | No  |
| Run                       | Team 2 | `run-360`          | exact detail only                                         | Prefix probing would leak identifiers                         | `console:read`       | No  |
| Pathway                   | Team 1 | `pathway-360`      | inventory search exists                                   | Contract is POST topology-oriented, not lightweight discovery | `console:read`       | No  |
| Incident / event storm    | Team 3 | incident routes    | list filters do not document label/ID search              | No approved search filter                                     | `console:read`       | No  |
| Kafka cluster/topic/group | Team 1 | stream routes      | inventory filters exist                                   | Search semantics not proven for every entity                  | `console:read`       | No  |
| Connector/schema subject  | Team 1 | stream routes      | exact detail only                                         | No bounded inventory search                                   | `console:read`       | No  |
| Integration               | Team 4 | integration route  | configuration list                                        | No operational entity search contract                         | `console:read`       | No  |

All included APIs are tenant-header and environment-query scoped, return opaque IDs and labels, and use cursor/first-page semantics. Providers request deterministic `name` ordering where supported and map evidence without converting missing values to zero. Unsupported types are not invoked or locally scanned.
