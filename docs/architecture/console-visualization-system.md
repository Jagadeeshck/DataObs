# Console visualization system

`src/visualization` separates semantic contracts, tokens, formatting, interaction, and focused primitives. Elastic Charts owns bounded operational series; Cytoscape is lazy-loaded by the bounded topology wrapper; a tiny SVG path is reserved for sparklines. Defaults cap series at 2,000 points and topology at 100 nodes/200 edges. Capability APIs must bound/downsample before transfer; the browser neither invents evidence nor recomputes anomaly, forecast, health, confidence, impact, reliability, severity, causality, or traversal.

Complex visuals always include semantic table/list alternatives. Missing values remain `null` gaps, measured zero remains `0`, and unavailable state replaces axes. Time is formatted in UTC. Feature adapters may cross-highlight only authoritative IDs and must require an explicit action before changing global time.
