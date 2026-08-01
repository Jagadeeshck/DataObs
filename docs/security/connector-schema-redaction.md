# Connector and Schema redaction

The durable allowlist contains connector identity, measured state/counts, bounded task summaries, worker IDs, health evidence, and configuration/class fingerprints. The persistence boundary rejects the configuration object entirely; redacting individual keys is not sufficient. Responses use the same safe source allowlist and exclude full traces.

Schema persistence stores only subject/version identity, type, fingerprint, compatibility label, reference count/list and bounded semantic summaries. Complete Avro, JSON Schema and Protobuf definitions, registry credentials and request authorization metadata are excluded. Logs record safe error categories rather than response bodies.
