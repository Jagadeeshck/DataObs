
## Google Pub/Sub messaging

The optional Google Pub/Sub collector is registered as `gcp` v1. It uses official Pub/Sub admin and Cloud Monitoring
read clients, explicit project allowlists, and never exposes message consumption or mutation operations. See
`config/integrations/gcp-pubsub-messaging.example.yaml`.

## MySQL database

Use `config/integrations/mysql-database.example.yaml` and install the optional `requirements-mysql.txt`. The Team 4 v1 provider requires verified TLS and shared secret references, collects fixed structural metadata, and permits business-table access only for explicit generated aggregate policies.
