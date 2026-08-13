# Team 4 RabbitMQ collector access

Use a dedicated `dataobs_monitor` account with the RabbitMQ `monitoring` tag. Grant empty regular-resource permissions in every collected vhost: configure `^$`, write `^$`, and read `^$`. The collector does not require `administrator`, `policymaker`, or `management` tags and must fail rather than broaden access.

Store the password in an `env:` or `file-ref:` reference. Production endpoints require HTTPS, certificate verification, hostname verification, and referenced (never inline) CA material. Authorization, cookies, server response bodies, usernames, and endpoints containing credentials must never enter evidence or logs.

This account accesses only GET Management HTTP API inventory and health endpoints. It cannot declare, modify, publish, retrieve, consume, acknowledge, or delete broker objects or messages.
