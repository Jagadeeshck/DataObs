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
DATAOBS_ALLOW_UNAUTHENTICATED_DEV  true/false dev-only no-token mode (default: true)
LOG_LEVEL               Python log level (default: INFO)
"""
from __future__ import annotations

import logging

import uvicorn

from src.api.app import create_app, settings_from_env


def main() -> None:
    settings = settings_from_env()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    app = create_app(settings=settings)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
