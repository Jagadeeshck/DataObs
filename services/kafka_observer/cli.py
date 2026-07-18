from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from integrations.kafka.admin_client import ConfluentReadOnlyAdmin
from integrations.kafka.config import KafkaObserverConfig
from packages.elastic_store.client import make_client

from .checkpoint_store import MemoryCheckpointStore
from .collector_registry import CAPABILITIES, CapabilityBinding
from .repository import ElasticsearchObserverRepository
from .service import KafkaObserverService


def _secret(reference: str | None) -> str | None:
    if not reference:
        return None
    if reference.startswith("env:"):
        name = reference[4:]
        if name not in os.environ:
            raise ValueError(f"secret environment reference is not set: {name}")
        return os.environ[name]
    if reference.startswith("file:"):
        return Path(reference[5:]).read_text().strip()
    raise ValueError("secrets must use env: or file: references")


def _load(path: str) -> KafkaObserverConfig:
    config = KafkaObserverConfig.model_validate(yaml.safe_load(Path(path).read_text()))
    if config.security.protocol in {"PLAINTEXT", "SASL_PLAINTEXT"} and config.environment.lower() not in {
        "dev",
        "development",
        "test",
    }:
        raise ValueError("insecure Kafka transport is allowed only in development/test")
    return config


def _client_config(config: KafkaObserverConfig) -> dict[str, Any]:
    result: dict[str, Any] = {
        "bootstrap.servers": ",".join(config.bootstrap_servers),
        "client.id": config.client_id,
        "security.protocol": config.security.protocol,
    }
    if config.security.sasl_mechanism:
        result["sasl.mechanism"] = config.security.sasl_mechanism
        result["sasl.username"] = _secret(config.security.username_ref)
        result["sasl.password"] = _secret(config.security.password_ref)
    for key, value in (
        ("ssl.ca.location", config.security.ca_file),
        ("ssl.certificate.location", config.security.certificate_file),
        ("ssl.key.location", config.security.key_file),
    ):
        if value:
            result[key] = value
    return result


def _service(config: KafkaObserverConfig) -> tuple[KafkaObserverService, ConfluentReadOnlyAdmin]:
    admin = ConfluentReadOnlyAdmin(_client_config(config), timeout=config.request_timeout_seconds)
    repository = ElasticsearchObserverRepository(
        make_client(), config.tenant_id, config.environment, config.integration_id
    )
    bindings = [
        CapabilityBinding(
            capability=c,
            selected_provider="kafka_admin",
            collection_interval_seconds=30,
            source_integration_id=config.integration_id,
            source_event_identity="kafka-admin",
            deduplication_key=f"{config.integration_id}:{c}",
        )
        for c in ("configuration_inventory", "offset_inventory")
    ]
    return KafkaObserverService(admin, MemoryCheckpointStore(), bindings, repository=repository), admin


def main() -> int:
    parser = argparse.ArgumentParser(prog="dataobs-kafka-observer")
    parser.add_argument(
        "command", choices=["run", "test-connection", "inventory", "collect-once", "print-capabilities"]
    )
    parser.add_argument("--config", default=os.getenv("DATAOBS_KAFKA_CONFIG", "config/kafka-observer.example.yaml"))
    parser.add_argument("--interval", type=float, default=30)
    args = parser.parse_args()
    if args.command == "print-capabilities":
        print(json.dumps(sorted(CAPABILITIES)))
        return 0
    config = _load(args.config)
    service, admin = _service(config)
    try:
        if args.command == "test-connection":
            print(json.dumps(admin.test_connection(), sort_keys=True))
        elif args.command == "inventory":
            print(json.dumps(admin.inventory(), sort_keys=True))
        elif args.command == "collect-once":
            print(json.dumps(service.collect_once(), sort_keys=True))
        else:
            stopping = False

            def stop(*_: object) -> None:
                nonlocal stopping
                stopping = True

            signal.signal(signal.SIGTERM, stop)
            signal.signal(signal.SIGINT, stop)
            while not stopping:
                service.collect_once()
                time.sleep(args.interval)
    finally:
        admin.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
