# Multi-broker console experience

`/streams` remains the stable URL and is presented as **Messaging**. It first loads a provider estate from the bounded capability endpoint, then retains the Kafka inventory for backward compatibility. Tenant/environment changes abort the in-flight request and clear prior evidence. One provider state never implies global estate health; stale or unavailable evidence produces a partial estate message.

The UI presents only systems returned by the endpoint. Bounded resource pages may be added when provider-neutral server inventories exist. Legacy Kafka cluster, topic, consumer-group, connector, and schema routes remain authoritative.
