# Provider-neutral stream model

Messaging identity hashes tenant, environment, system, provider account/project/subscription scope, region/location, namespace, resource kind, and provider resource ID. A display name is never identity. Resources preserve queue, stream, topic, exchange, subscription, shard, partition, group, and dead-letter kinds.

`MessagingBacklog` is an umbrella evidence contract, not offset lag. It retains metric, method, unit, confidence, coverage, and missing inputs. Zero is a measurement; absence remains null. `MessagingLag` is restricted to offset, sequence, time, or iterator-age evidence. Typed facets are bounded allowlists, never raw provider responses.

Provider-neutral routes carry system and resource identity, allowing graph hashes and pathways to distinguish Kafka-to-Kafka from Kafka-to-SQS changes. Trace-derived latency is preferred; provider estimates are labelled and unavailable evidence is not synthesized.
