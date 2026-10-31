"""Runnable entrypoint for the FastAPI-based DataObs API.

Environment variables
---------------------
API_TOKEN               Shared bearer token for all clients
API_HOST                Bind host (default: 0.0.0.0)
API_PORT                Bind port (default: 8080)
ELASTICSEARCH_URL       ES endpoint (default: http://localhost:9200)
ELASTICSEARCH_USER      ES username (default: elastic)
ELASTICSEARCH_PASSWORD  ES password (default: "")
DATAOBS_STORE_BACKEND   "elasticsearch" | "memory" (default: memory)
DATAOBS_TENANT_ID       Tenant ID for index partitioning (default: default)
DATAOBS_ALLOW_UNAUTHENTICATED_DEV  true/false dev-only no-token mode (default: false)

    WARNING: Setting this to true bypasses ALL authentication. It is only
    permitted when DATAOBS_ENV=development and DATAOBS_AUTH_PROVIDER=local.
    NEVER set to true in a shared, staging, or production environment.
    Production startup will hard-fail if this flag is true.

LOG_LEVEL               Python log level (default: INFO)
"""

from __future__ import annotations

import logging

import uvicorn

from src.api.app import create_app, settings_from_env


def main() -> None:
    from src.telemetry import init_telemetry

    init_telemetry()
    settings = settings_from_env()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    if settings.auth.allow_unauthenticated_dev:
        logging.getLogger(__name__).warning(
            "SECURITY WARNING: DATAOBS_ALLOW_UNAUTHENTICATED_DEV=true — "
            "all requests are accepted without authentication. "
            "This mode is ONLY permitted for local development. "
            "Never use in a shared or production environment."
        )
    app = create_app(settings=settings)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
