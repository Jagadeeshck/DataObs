# Console performance troubleshooting

Run `pnpm build && pnpm bundle:check && pnpm performance:check`. The deterministic gate checks total JavaScript (5.5 MB), largest chunk (1.5 MB), CSS (500 kB), and JavaScript chunk count (100). These thresholds are regression budgets, not production percentiles.

Correlate slow stable route IDs with LCP/INP/long tasks and API span counts. Check graph initialization for Cytoscape, chart chunks for Elastic Charts, repeated polling, duplicate requests, and tables rendering unbounded rows. Compare only bounded `service.version` dimensions. Product targets are LCP p75 ≤2.5 s, INP p75 ≤200 ms, CLS p75 ≤0.1; CI cannot prove those percentiles. Revert optional telemetry by runtime switch if instrumentation itself is implicated.
