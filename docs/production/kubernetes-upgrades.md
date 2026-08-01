# Kubernetes upgrades and rollback

Back up external Elasticsearch, render new digest pins, and run `helm upgrade`. The bounded pre-upgrade migration hook must succeed before workloads change. Existing migrations are forward-only and immutable. `helm rollback` restores Kubernetes manifests and image configuration but **does not roll back Elasticsearch schema or data**; ensure the old application is schema compatible. Retain Job logs and diagnostics before cleanup.
