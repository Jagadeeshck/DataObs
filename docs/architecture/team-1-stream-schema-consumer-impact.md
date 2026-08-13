# Team 1 streaming schema compatibility and consumer impact

Schema Registry metadata flows through bounded observation, transient parsing, structural summarization, compatibility evaluation, resource/application binding, consumer exposure, and existing pathway/product context. Raw schemas are discarded after evaluation.

Compatibility and consumer health are separate. An incompatible producer schema plus a bound consumer yields `potentially_exposed` unless accepted-version evidence proves incompatibility. `degradation_observed` requires independent runtime evidence. Temporal correlation uses “after” language and never claims causality.

Supported formats are AVRO, PROTOBUF descriptor summaries, JSON_SCHEMA, and UNKNOWN. Policies are NONE, BACKWARD, BACKWARD_TRANSITIVE, FORWARD, FORWARD_TRANSITIVE, FULL, FULL_TRANSITIVE, and UNKNOWN. Every result reports method, authority, confidence, limitations, and missing inputs.

Stable identities include tenant, environment, registry integration, subject, version/fingerprint, and resource where relevant. TopicNameStrategy is resolved only when declared; RecordNameStrategy and TopicRecordNameStrategy remain unresolved without instrumentation or reviewed mapping.
