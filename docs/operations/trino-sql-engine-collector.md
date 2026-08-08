# Operating the Trino collector

Install the optional dependency with `pip install -r requirements-trino.txt`; there is no runtime installation. Configure a structured host/port, verified TLS, secret references, bounded metadata/runtime scopes, and catalog allowlists. OAuth2 browser/token caching and Kerberos are deferred. Run default fake-client tests without Trino; opt into the disposable/synthetic live suite with `RUN_TRINO_INTEGRATION_TESTS=1`.

Each family (`catalogs`, `schemas`, `relations`, `columns`, `materialized_views`, `cluster_health`, `runtime_queries`, `runtime_tasks`) is isolated. Checkpoint keys include trusted tenant/environment/integration, provider, hashed cluster, family, and optional catalog. Persist observations before OCC checkpoint advancement; failed scopes do not advance while successful siblings may. A checkpoint cannot make bounded upstream history durable.
