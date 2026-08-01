# Kafka observer secret handling

Kafka credentials must be indirect `env:` or `file:` references and TLS verification cannot be disabled. Bootstrap entries cannot contain URL credentials. Kafka Connect collection drops password-like fields, credential-bearing connection URLs, complete configuration, and task traces; only an approved safe subset and fingerprints are retained. Schema Registry collection stores fingerprints, references, compatibility, and bounded structural summaries, never unrestricted raw schemas.

Collection errors contain categories and fingerprints, not exception bodies that could disclose endpoints or credentials. The observer provides no message inspection or automatic remediation.
