# Kafka Connect adapter

Read-only inventory and status collection uses an injected transport and an allowlisted HTTPS endpoint. Configuration is allowlisted before fingerprinting or persistence. The sole mutation boundary restarts a specifically identified failed task and requires an approved request; connector creation and arbitrary configuration mutation are unsupported.
