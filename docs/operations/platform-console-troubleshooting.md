# Platform Console troubleshooting

* **Platform evidence is partial:** one or more independent APIs timed out or failed. Use manual **Refresh evidence** after checking API availability.
* **Unauthorised:** confirm the principal has `platform_operations:read`; inventory endpoints can additionally enforce resource read permissions.
* **Unvalidated capacity:** this is authoritative current status, not a UI failure. Consult the returned capacity profile reference.
* **Unknown health/drift:** lifecycle state cannot substitute for missing evidence.
* **Resource unavailable:** it may have been removed or the caller may lack its resource permission. Request IDs remain in API diagnostics rather than exposing raw exceptions.

The Console never calls Elasticsearch, Kubernetes, Terraform, Helm or remote-command endpoints.
