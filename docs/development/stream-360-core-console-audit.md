# Stream 360 Core Console audit

The backend projections expose stream/topic identity, cluster, health and reason codes, partition and replication counts, records/bytes rates, lag and retention risk, consumer-group counts, safe configuration, source coverage and observation time. Consumer-group projections expose identity, cluster/state, members, assignments, offsets, lag intelligence, rebalances and retention risk. Every endpoint uses the evidence envelope (`data_status`, `observed_at`, `source_coverage`, `confidence`, `warnings`, `missing_inputs`, and `request_id`). Fields absent from those projections are not presented.

Before this change the list route applied only tenant/environment and pagination. It now applies bounded `search`, `health`, `retention_risk`, `cluster_id`, `consumer_group_id`, and measured-lag filters, with the approved sorts. Search uses a match query rather than user-controlled wildcards. Cursor signatures bind the tenant, environment, complete filters, route/resource and sort.

Measured sections are overview, partitions, metrics/throughput, related consumer groups, safe configuration and pathways for topics; and overview, members, assignments, offsets, lag/heatmap, retention risk and rebalances for groups. Incidents retain the existing measured projection behavior.

The old generic renderer converted absent numeric values to an `Unknown` string but serialized nested values as JSON; upstream producer code must also avoid defaulting missing offsets to zero. Core views now preserve numeric zero while rendering null/absent as Unknown, configuration absence as Not configured, endpoint failure as Unavailable and envelope staleness as Stale.

Existing Console patterns include aborting fetches on effect cleanup, URL-backed tabs/filters, focusable responsive table wrappers, semantic tables, ARIA tabs/status/alerts, keyboard arrow navigation, and global reduced-motion CSS. The core views extend those patterns with labelled grid cells and mandatory table alternatives.
