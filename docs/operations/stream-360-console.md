# Stream 360 Core Console

Supported pages are Streams Inventory, Topic 360, and Consumer Group 360. Inventory supports search, cluster, health, retention risk, measured lag, observation freshness, and approved sorting; state is URL-backed and a filter change discards the search-after cursor.

Evidence distinguishes measured zero from `unknown`, `not_configured`, `unavailable`, and `stale`. Missing offsets are Unknown, never zero. Manual refresh is available. Detail requests are cancelled when the view or tenant/environment changes; polling, when enabled by the host, is a 30-second refresh and is not described as streaming.

Partition health and lag heatmaps have keyboard-focusable labelled cells and semantic table alternatives. Charts include a textual latest-value/sample-count summary and units and honor reduced motion. Long IDs and tables wrap or scroll within the page.

Only safe topic configuration keys are displayed. Credentials, JAAS, arbitrary client metadata, message inspection, and write actions are excluded. Cluster, Connector, Schema and Pathway page redesigns are intentionally deferred.
