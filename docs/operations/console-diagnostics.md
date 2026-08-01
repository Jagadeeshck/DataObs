# Console diagnostics

`/diagnostics/console` is hidden from navigation and requires `console:admin`. It shows only current-session configuration validity, enabled state, collector origin (no path/credentials), sample ratio, stable route ID, online state, export state, bounded queue/drop counts, error fingerprint, browser support, and observed metrics.

Operators may copy the explicit safe projection, clear in-memory state, create a synthetic safe event, or perform a credential-free bounded connectivity HEAD request. The page never reads or displays identity, tenant data, cookies, browser storage, endpoint paths, payloads, headers, or stacks. Normal users receive an accessible access-denied view.
