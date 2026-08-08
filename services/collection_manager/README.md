# Collection Manager

Minimal tenant-aware control plane for source, integration, collector, scanner, heartbeat, scan-policy, scanner-task, and synthetic scanner-result workflows. Fleet and EDOT adapters are explicit `not_implemented` boundaries.

## BigQuery provider

The explicit registry includes BigQuery warehouse collector v1. Its official Google dependencies are optional and lazy; configuration requires explicit projects/locations. See `docs/integrations/bigquery.md`.
