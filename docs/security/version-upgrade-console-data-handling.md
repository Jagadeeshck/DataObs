# Version upgrade Console data handling

Access requires `platform_operations:read`; direct navigation is permission gated before the page mounts. Presentation is typed and allowlisted. Telemetry may include page, state enums, blocker-count bucket and duration bucket. It must not include installation, cluster or environment identifiers, exact private builds, evidence SHAs, raw configuration, CI environment, endpoints, credentials, Helm values, manifests, migration payloads, or arbitrary backend JSON. The client makes GET assessment requests only.
