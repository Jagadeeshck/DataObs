from __future__ import annotations

import argparse
import json
import os
import signal
import uuid
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from integrations.kafka.admin_client import ConfluentReadOnlyAdmin
from integrations.kafka.config import KafkaObserverConfig
from integrations.kafka_connect.client import KafkaConnectClient
from integrations.kafka_connect.collector import KafkaConnectCollector
from integrations.kafka_connect.config import KafkaConnectConfig
from integrations.schema_registry.client import SchemaRegistryClient
from integrations.schema_registry.collector import SchemaRegistryCollector
from integrations.schema_registry.config import SchemaRegistryConfig
from packages.elastic_store.client import make_client

from .broker_metrics import broker_metric_status
from .checkpoints import DurableCheckpointStore
from .collector_registry import CAPABILITIES, CapabilityBinding
from .groups import group_projection
from .inventory import inventory_projection
from .leases import DurableLeases
from .repository import ElasticsearchObserverRepository
from .scheduler import CollectionScheduler, ScheduledCollection
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


class _HttpTransport:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, *, timeout: float) -> Any:
        import requests

        response = requests.get(self.base_url + path, timeout=timeout)
        response.raise_for_status()
        return response.json()


def _service(
    config: KafkaObserverConfig,
) -> tuple[KafkaObserverService, ConfluentReadOnlyAdmin, ElasticsearchObserverRepository]:
    admin = ConfluentReadOnlyAdmin(_client_config(config), timeout=config.request_timeout_seconds)
    repository = ElasticsearchObserverRepository(
        make_client(), config.tenant_id, config.environment, config.integration_id
    )
    connect = None
    if config.kafka_connect_url:
        cc = KafkaConnectConfig(
            base_url=config.kafka_connect_url,
            allowed_hosts=config.kafka_connect_allowed_hosts,
            timeout_seconds=config.request_timeout_seconds,
        )
        connect = KafkaConnectCollector(
            KafkaConnectClient(cc, _HttpTransport(config.kafka_connect_url)),
            maximum_connectors=config.maximum_connectors,
        )
    schemas = None
    if config.schema_registry_url:
        sc = SchemaRegistryConfig(
            base_url=config.schema_registry_url,
            allowed_hosts=config.schema_registry_allowed_hosts,
            timeout_seconds=config.request_timeout_seconds,
        )
        schemas = SchemaRegistryCollector(
            SchemaRegistryClient(sc, _HttpTransport(config.schema_registry_url)),
            maximum_subjects=config.maximum_subjects,
            maximum_versions=config.maximum_schema_versions,
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
    return (
        KafkaObserverService(
            admin,
            DurableCheckpointStore(repository),
            bindings,
            repository=repository,
            connect_collector=connect,
            schema_collector=schemas,
        ),
        admin,
        repository,
    )


def _emit(command: str, result: Any) -> None:
    print(json.dumps({"command": command, "schema_version": "1.0", "result": result}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(prog="dataobs-kafka-observer")
    parser.add_argument(
        "command",
        choices=[
            "run",
            "collect-once",
            "test-connection",
            "inventory",
            "offsets",
            "groups",
            "connectors",
            "schemas",
            "broker-metrics",
            "status",
            "print-capabilities",
        ],
    )
    parser.add_argument("--config", default=os.getenv("DATAOBS_KAFKA_CONFIG", "config/kafka-observer.example.yaml"))
    parser.add_argument("--interval", type=float, default=30)
    args = parser.parse_args()
    if args.command == "print-capabilities":
        _emit(args.command, {"capabilities": sorted(CAPABILITIES)})
        return 0
    config = _load(args.config)
    service, admin, repository = _service(config)
    try:
        if args.command == "test-connection":
            _emit(args.command, admin.test_connection())
        elif args.command == "inventory":
            _emit(args.command, inventory_projection(admin.inventory()))
        elif args.command == "groups":
            _emit(args.command, group_projection(admin.inventory()))
        elif args.command == "offsets":
            _emit(args.command, admin.offsets(maximum=config.maximum_combinations_per_cycle))
        elif args.command == "broker-metrics":
            _emit(args.command, broker_metric_status())
        elif args.command in {"connectors", "schemas"}:
            _emit(args.command, service.collect_capability(args.command)["result"])
        elif args.command == "status":
            states = {
                name: "not_configured" if collector is None else "available"
                for name, collector in (
                    ("kafka_connect", service.connect_collector),
                    ("schema_registry", service.schema_collector),
                )
            }
            try:
                repository.es.info()
                kafka = admin.test_connection()
                ready, elastic = bool(kafka.get("ok")), "available"
            except Exception as error:
                ready, elastic = False, type(error).__name__
            checkpoints = {name: repository.load_checkpoint(name) for name in ("inventory", "groups", "offsets")}
            _emit(
                args.command,
                {
                    "ready": ready,
                    "live": True,
                    "integration_id": config.integration_id,
                    "lease_status": "available" if ready else "unknown",
                    "elasticsearch_status": elastic,
                    "migration_status": "0021_lineage_analysis_explorer",
                    "provider_capability_states": states
                    | {"kafka_admin": "available" if ready else "source_unavailable"},
                    "checkpoints": checkpoints,
                },
            )
        elif args.command == "collect-once":
            _emit(args.command, service.collect_once())
        else:
            intervals = {
                "inventory": config.inventory_interval_seconds,
                "groups": config.group_interval_seconds,
                "offsets": config.offset_interval_seconds,
                "connectors": config.connect_interval_seconds,
                "schemas": config.schema_interval_seconds,
            }
            scheduler = CollectionScheduler(
                [
                    ScheduledCollection(name, seconds, lambda name=name: service.collect_capability(name))
                    for name, seconds in intervals.items()
                ],
                DurableLeases(repository),
                str(uuid.uuid4()),
                lease_seconds=config.lease_duration_seconds,
                renewal_seconds=config.lease_renewal_seconds,
            )
            signal.signal(signal.SIGTERM, lambda *_: scheduler.stop())
            signal.signal(signal.SIGINT, lambda *_: scheduler.stop())
            scheduler.run()
    finally:
        admin.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, PermissionError) as error:
        print(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "error": {"category": type(error).__name__, "message": "configuration rejected"},
                }
            )
        )
        raise SystemExit(2) from None
    except Exception as error:
        print(
            json.dumps(
                {"schema_version": "1.0", "error": {"category": type(error).__name__, "message": "collection failed"}}
            )
        )
        raise SystemExit(1) from None
