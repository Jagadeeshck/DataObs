# Operating the Presto SQL engine collector

Install `requirements-presto.txt` only in the collector image. Configuration is closed and requires a DNS hostname, HTTPS, TLS verification, Basic authentication, and an environment-backed password reference. A CA bundle may use an `env:` or absolute `file-ref:` reference. Inline secrets, IP literals, URLs, headers, roles, session properties, proxies, extra credentials, and impersonation are rejected.

The provider fixes `X-Presto-Source` through `source=dataobs-collector`, uses autocommit, and performs no session mutation. Every HTTP protocol request is confined to the configured HTTPS host and port with redirects disabled, protecting `nextUri` continuation.

Collections are bounded by rows, pages, fetch size, statements, observation count, and deadline. Catalog failures are isolated. A runtime permission or metadata-shape failure disables that family without discarding independent evidence. HTTP 503 is `server_busy` and retryable; authentication, TLS, configuration, and permission failures are not.

Run fake-client tests with `pytest -q tests/integrations/test_presto_provider.py`. Set `RUN_PRESTO_INTEGRATION_TESTS=1` and trusted `PRESTO_HOST`/`PRESTO_PORT` only for a disposable server. Status remains `functional_unvalidated` until hosted exact-commit evidence is retained and independently verified.
