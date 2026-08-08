# Adaptive monitor data handling

Adaptive detection accepts scalar observations and bounded aggregate profiles; it rejects raw rows, arbitrary SQL, secrets, credentials, unbounded histogram labels and unlimited categories. Numerical histograms cap at 100 buckets and categorical top-K at 50. Redaction collapses prohibited labels.

Every repository query must bind trusted tenant/environment context and return 404 across scopes. History windows and result pages are bounded; append evidence uses deterministic create-only IDs and projections use OCC. Reset/change actors come only from authenticated principals. Telemetry labels contain bounded monitor/signal state—not asset or column names.
