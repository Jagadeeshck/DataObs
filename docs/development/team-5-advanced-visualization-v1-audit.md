# Team 5 advanced visualization v1 audit

Audited base: `d4f511ebb331b74528426b91ce69bd24f8993eac` (local `main`; no Git remote was configured, so fetch/open-PR inspection and hosted run lookup were unavailable). PR #248 is present at `7fb4a66`; merges after it through #244 were inspected via the local 40-commit log. Terminal migration is derived by the repository script, never hard-coded.

## Dependency decision

The Console already pins Elastic Charts 71.5.1, EUI 117.0.0, and Cytoscape 3.33.1. No dependency was added. Elastic Charts is the operational-series layer. Cytoscape was previously eagerly imported by Flow Map; the shared wrapper dynamically imports it. Tiny repeated sparklines use bounded, accessible SVG to avoid hundreds of chart engines.

| Surface                  | Visualization         | Current implementation         | Data semantics               | Reusable | Proposed primitive                   |
| ------------------------ | --------------------- | ------------------------------ | ---------------------------- | -------- | ------------------------------------ |
| Dashboards               | cards/lists           | feature JSX and CSS            | health, coverage, priority   | partial  | MetricCard, Distribution, RankedList |
| Command Center           | health badges/cards   | Evidence components            | health, partial, unavailable | partial  | MetricCard, HealthMatrix             |
| Activity / Investigation | event lists           | feature lists/timeline adapter | provenance-bearing evidence  | partial  | EvidenceTimeline                     |
| Flow Map / Pathways      | topology              | direct Cytoscape import        | capability-owned nodes/edges | no       | TopologyGraph adapter                |
| Streams                  | metrics/tables        | feature HTML                   | throughput, provider health  | partial  | TimeSeries, OperationalTable         |
| Quality                  | metric/evidence cards | feature JSX                    | observed, anomaly, baseline  | partial  | TimeSeries overlays                  |
| Jobs                     | run lists             | tables/lists                   | actual/expected/missing run  | partial  | Timeline, OperationalTable           |
| Lineage                  | impact/topology       | feature graph/list             | impact and confidence        | partial  | TopologyGraph + separate metrics     |
| Incidents                | severity/timeline     | badges/lists                   | severity, lifecycle          | partial  | StatusDistribution, Timeline         |
| Global CSS               | semantic colors       | hard-coded feature classes     | mixed                        | no       | visualization CSS variables          |

Repository search covered chart/SVG/canvas/Cytoscape/table/card/badge/timeline/topology/widget/evidence, inline `style`, and hex/rgb colors. Existing EUI usage is capability-local; this package uses semantic HTML to preserve lightweight accessible alternatives. Migration should remain presentation-only and incremental because domain provider contracts are authoritative.

## Baseline

The checkout was clean. Remote preflight was blocked because no `origin` exists. Baseline commands are recorded in the PR report/evidence; failures must include their literal command output rather than the label “pre-existing.” This work does not modify migrations or generated API schema.
