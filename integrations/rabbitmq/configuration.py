from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

from .authentication import BasicAuthentication, parse_authentication
from .errors import error


def _closed(raw, allowed, family="configuration"):
    if not isinstance(raw, Mapping) or set(raw) - set(allowed):
        raise error("invalid_configuration", family)


def _integer(raw, key, default, high):
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= high:
        raise error("invalid_configuration", "limits")
    return value


@dataclass(frozen=True)
class TlsConfiguration:
    verify_certificate: bool
    verify_hostname: bool
    ca_bundle_ref: str | None


@dataclass(frozen=True)
class RabbitMqConfiguration:
    endpoint: str
    authentication: BasicAuthentication
    tls: TlsConfiguration
    discovery: Mapping[str, object]
    statistics: Mapping[str, bool]
    limits: Mapping[str, int]


def parse_configuration(raw: Mapping[str, Any]) -> RabbitMqConfiguration:
    _closed(raw, {"endpoint", "authentication", "tls", "discovery", "statistics", "limits"})
    endpoint = raw.get("endpoint")
    if not isinstance(endpoint, str):
        raise error("invalid_configuration", "endpoint")
    parsed = urlsplit(endpoint)
    localhost = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise error("invalid_configuration", "endpoint")
    if not parsed.hostname or parsed.scheme not in ({"http", "https"} if localhost else {"https"}):
        raise error("invalid_configuration", "endpoint")
    tls = raw.get("tls", {})
    _closed(tls, {"verify_certificate", "verify_hostname", "ca_bundle_ref"}, "tls")
    verify_certificate = tls.get("verify_certificate", True)
    verify_hostname = tls.get("verify_hostname", True)
    ca_ref = tls.get("ca_bundle_ref")
    if not isinstance(verify_certificate, bool) or not isinstance(verify_hostname, bool):
        raise error("invalid_configuration", "tls")
    if (not localhost or parsed.scheme == "https") and (not verify_certificate or not verify_hostname):
        raise error("invalid_configuration", "tls")
    if ca_ref is not None and (not isinstance(ca_ref, str) or not ca_ref.startswith("file-ref:")):
        raise error("credential_reference_invalid", "tls")
    discovery = raw.get("discovery", {})
    discovery_keys = {
        "include_vhosts",
        "exclude_vhosts",
        "include_queues",
        "exclude_queues",
        "include_exchanges",
        "include_bindings",
        "include_dead_letter_relationships",
        "include_cluster_health",
        "include_node_summary",
    }
    _closed(discovery, discovery_keys, "discovery")
    defaults = {
        "include_vhosts": (),
        "exclude_vhosts": (),
        "include_queues": (),
        "exclude_queues": (),
        "include_exchanges": True,
        "include_bindings": True,
        "include_dead_letter_relationships": True,
        "include_cluster_health": True,
        "include_node_summary": True,
    }
    discovery = {**defaults, **discovery}
    for key in ("include_vhosts", "exclude_vhosts", "include_queues", "exclude_queues"):
        if not isinstance(discovery[key], (list, tuple)) or not all(isinstance(x, str) for x in discovery[key]):
            raise error("invalid_configuration", "discovery")
        discovery[key] = tuple(discovery[key])
    statistics = raw.get("statistics", {})
    stat_keys = {"include_queue_counters", "include_exchange_counters", "include_delivery_counters"}
    _closed(statistics, stat_keys, "statistics")
    statistics = {key: statistics.get(key, True) for key in stat_keys}
    if not all(isinstance(x, bool) for x in statistics.values()):
        raise error("invalid_configuration", "statistics")
    limits = raw.get("limits", {})
    limit_specs = {
        "page_size": (100, 500),
        "maximum_pages": (100, 1000),
        "maximum_vhosts": (1000, 1000),
        "maximum_queues": (100000, 100000),
        "maximum_exchanges": (100000, 100000),
        "maximum_bindings": (500000, 500000),
        "maximum_observations": (1000000, 1000000),
        "request_timeout_seconds": (10, 120),
        "total_timeout_seconds": (300, 3600),
        "maximum_response_bytes": (10485760, 52428800),
    }
    _closed(limits, limit_specs, "limits")
    bounded = {key: _integer(limits, key, default, high) for key, (default, high) in limit_specs.items()}
    return RabbitMqConfiguration(
        endpoint.rstrip("/"),
        parse_authentication(raw.get("authentication")),
        TlsConfiguration(verify_certificate, verify_hostname, ca_ref),
        discovery,
        statistics,
        bounded,
    )
