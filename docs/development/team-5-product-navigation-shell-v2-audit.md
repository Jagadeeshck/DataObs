# Team 5 — Product Navigation, Workspaces & Context Shell v2 audit

**Audited base:** `d006339b3f855b67a63bd4625d42d2f1688a354c`  
**Terminal migration:** `0029_team2_data_intelligence_reconciliation`  
**Console routes audited:** 55

## Preflight and change review

The audit inspected the merge history through PR #243, including Activity Center (#238), Operational Dashboards (#231), Investigation Workspace (#227), multi-broker messaging (#243), pathway investigation (#232), Data Contracts (#226), Elastic Cases/Workflows (#235 and #241), and platform lifecycle (#230). The checkout has no configured Git remote and GitHub CLI is unauthenticated, so current open-PR file inspection could not be independently refreshed; this is a recorded limitation rather than evidence of no conflicts.

## Decisions

- The route registry remains the only route, permission, ownership, discovery, parent, and navigation metadata source.
- Six intent-oriented workspaces replace the flat capability rail. Detail/entity routes remain link/search-only.
- Shell terminology is provider-neutral: **Streams** and **Messaging** are used globally; Kafka-specific labels remain only on genuinely Kafka-specific details.
- Workspace is presentation metadata, never an authorization boundary.

## Complete route matrix

| Route | Path | Team | Current group | Workspace | Capability | Parent | Permission | Availability | Quick Find | Global Search | Navigation level | Primary capability nav | Search/link only |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `command-center` | `/` | `team-5` | Overview | `home` | `command-center` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `activity-center` | `/activity` | `team-5` | Overview | `home` | `activity` | `—` | `console:read` | available | Yes | No | Secondary | Yes | No |
| `flow` | `/flow` | `team-5` | Overview | `observe` | `unified-data-flow` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `global-search` | `/search` | `team-5` | Overview | `investigate` | `global-search` | `—` | `console:read` | available | Yes | No | Secondary | Yes | No |
| `investigation-workspace` | `/investigate` | `team-5` | Overview | `investigate` | `investigation` | `—` | `console:read` | available | Yes | No | Secondary | Yes | No |
| `dashboards` | `/dashboards` | `team-5` | Overview | `home` | `operational-dashboards` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `dashboard-view` | `/dashboards/:dashboardId` | `team-5` | Overview | `home` | `operational-dashboards` | `dashboards` | `console:read` | available | No | No | Search/link only | No | Yes |
| `pathways` | `/pathways` | `team-1` | Observe | `observe` | `pathways` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `pathway-360` | `/pathways/:pathwayId` | `team-1` | Observe | `observe` | `pathways` | `pathways` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `assets` | `/assets` | `team-2` | Observe | `observe` | `assets` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `data-contracts` | `/data-contracts` | `team-2` | Observe | `observe` | `data-contracts` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `data-contract-new` | `/data-contracts/new` | `team-2` | Configure | `observe` | `data-contracts` | `data-contracts` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `data-contract-360` | `/data-contracts/:contractId` | `team-2` | Observe | `observe` | `data-contracts` | `data-contracts` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `data-contract-version` | `/data-contracts/:contractId/versions/:version` | `team-2` | Observe | `observe` | `data-contracts` | `data-contract-360` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `asset-360` | `/assets/:assetId` | `team-2` | Observe | `observe` | `assets` | `assets` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `streams` | `/streams` | `team-1` | Observe | `observe` | `streams` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `streams-reliability` | `/streams/reliability` | `team-1` | Observe | `observe` | `streams` | `streams` | `console:read` | available | Yes | Yes | Contextual | Yes | No |
| `streams-intelligence` | `/streams/intelligence` | `team-1` | Observe | `observe` | `stream-intelligence` | `streams` | `console:read` | available | Yes | Yes | Contextual | Yes | No |
| `cluster-360` | `/streams/clusters/:clusterId` | `team-1` | Observe | `observe` | `streams` | `streams` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `topic-360` | `/streams/topics/:streamId` | `team-1` | Observe | `observe` | `streams` | `streams` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `consumer-group-360` | `/streams/consumer-groups/:groupId` | `team-1` | Observe | `observe` | `streams` | `streams` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `connector-360` | `/streams/connectors/:connectorId` | `team-1` | Observe | `observe` | `streams` | `streams` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `schema-360` | `/streams/schemas/:subjectId` | `team-1` | Observe | `observe` | `streams` | `streams` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `data-products` | `/data-products` | `team-2` | Observe | `observe` | `data-products` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `data-product-360` | `/data-products/:productId` | `team-2` | Observe | `observe` | `data-products` | `data-products` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `quality` | `/quality` | `team-4` | Observe | `observe` | `quality` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `monitors` | `/quality/monitors` | `team-4` | Observe | `observe` | `quality` | `quality` | `console:read` | available | Yes | Yes | Contextual | Yes | No |
| `monitor-new` | `/quality/monitors/new` | `team-4` | Observe | `observe` | `quality` | `monitors` | `console:read` | available | Yes | No | Search/link only | No | Yes |
| `monitor-360` | `/quality/monitors/:monitorId` | `team-4` | Observe | `observe` | `quality` | `monitors` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `jobs` | `/jobs` | `team-2` | Observe | `observe` | `jobs` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `job-360` | `/jobs/:jobId` | `team-2` | Observe | `observe` | `jobs` | `jobs` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `run-360` | `/runs/:runId` | `team-2` | Observe | `observe` | `jobs` | `jobs` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `run-comparison` | `/runs/compare` | `team-2` | Observe | `observe` | `jobs` | `jobs` | `console:read` | available | Yes | Yes | Search/link only | No | Yes |
| `lineage` | `/lineage` | `team-2` | Observe | `observe` | `lineage` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `incidents` | `/incidents` | `team-3` | Respond | `respond` | `incidents` | `—` | `incidents:read` | available | Yes | Yes | Secondary | Yes | No |
| `incident-workbench` | `/incidents/:incidentId` | `team-3` | Respond | `respond` | `incidents` | `incidents` | `incidents:read` | available | Yes | Yes | Search/link only | No | Yes |
| `event-storms` | `/incidents/event-storms` | `team-3` | Respond | `respond` | `incidents` | `incidents` | `incidents:read` | available | Yes | Yes | Contextual | Yes | No |
| `event-storm-detail` | `/incidents/event-storms/:floodId` | `team-3` | Respond | `respond` | `incidents` | `event-storms` | `incidents:read` | available | Yes | Yes | Search/link only | No | Yes |
| `correlation-group-detail` | `/incidents/correlation-groups/:groupId` | `team-3` | Respond | `respond` | `incidents` | `incidents` | `incidents:read` | available | Yes | Yes | Search/link only | No | Yes |
| `integrations` | `/integrations` | `team-5` | Configure | `integrate` | `integrations` | `—` | `integrations:read` | available | Yes | Yes | Secondary | Yes | No |
| `integration-detail` | `/integrations/:integrationId` | `team-5` | Configure | `integrate` | `integrations` | `integrations` | `integrations:read` | available | Yes | Yes | Search/link only | No | Yes |
| `onboarding` | `/onboarding` | `team-5` | Configure | `integrate` | `onboarding` | `—` | `console:read` | available | Yes | Yes | Secondary | Yes | No |
| `administration` | `/administration` | `team-5` | Configure | `admin` | `administration-access` | `—` | `iam:read` | available | Yes | Yes | Secondary | Yes | No |
| `administration-my-access` | `/administration/my-access` | `team-5` | Configure | `admin` | `administration-access` | `administration` | `auth:read` | available | Yes | Yes | Contextual | Yes | No |
| `administration-access` | `/administration/access` | `team-5` | Configure | `admin` | `administration-access` | `administration` | `iam:read` | available | Yes | Yes | Contextual | Yes | No |
| `administration-access-new` | `/administration/access/new` | `team-5` | Configure | `admin` | `administration-access` | `administration-access` | `iam:write` | available | No | No | Search/link only | No | Yes |
| `administration-access-detail` | `/administration/access/:bindingId` | `team-5` | Configure | `admin` | `administration-access` | `administration-access` | `iam:read` | available | Yes | Yes | Search/link only | No | Yes |
| `administration-audit` | `/administration/audit` | `team-5` | Configure | `admin` | `administration-access` | `administration` | `audit:read` | available | No | No | Search/link only | No | Yes |
| `administration-system` | `/administration/system` | `team-5` | Configure | `admin` | `administration-access` | `administration` | `auth:read` | available | Yes | Yes | Contextual | Yes | No |
| `administration-preferences` | `/administration/preferences` | `team-5` | Configure | `admin` | `administration-access` | `administration` | `auth:read` | available | Yes | Yes | Contextual | Yes | No |
| `console-diagnostics` | `/diagnostics/console` | `team-5` | System | `admin` | `console-observability` | `—` | `console:admin` | available | No | No | Search/link only | No | Yes |
| `login` | `/login` | `team-5` | System | `admin` | `authentication` | `—` | `console:read` | available | No | No | Search/link only | No | Yes |
| `auth-callback` | `/auth/callback` | `team-5` | System | `admin` | `authentication` | `—` | `console:read` | available | No | No | Search/link only | No | Yes |
| `logout` | `/logout` | `team-5` | System | `admin` | `authentication` | `—` | `console:read` | available | No | No | Search/link only | No | Yes |
| `unauthorised` | `/unauthorised` | `team-5` | System | `admin` | `shell` | `—` | `console:read` | available | No | No | Search/link only | No | Yes |

## Intent and configuration interpretation

Route capability IDs provide the owner-preserving primary intent. `home` starts work, `observe` explains systems and movement, `investigate` gathers evidence, `respond` coordinates incidents, `integrate` connects providers, and `admin` manages access/system configuration. Runtime capability state from authenticated context remains authoritative for configured, preview, unavailable, and not-configured presentation. Entity routes are never durable favourites and remain discoverable through bounded search or safe links only.
