# Stream capacity data handling

Capacity APIs accept trusted tenant/environment scope and resource identifiers only. They do not accept Elasticsearch
DSL, index names, provider endpoints, credentials, messages, or payloads. Repository reads always apply tenant and
environment filters. Evidence references are bounded metadata pointers and must not contain payload content.
