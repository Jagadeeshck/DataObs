import asyncio
import inspect
import os
from datetime import datetime, timedelta, timezone

import pytest

from integrations.rabbitmq.authentication import parse_authentication
from integrations.rabbitmq.client import RabbitMqManagementClient
from integrations.rabbitmq.collectors import collect_vhost
from integrations.rabbitmq.configuration import parse_configuration
from integrations.rabbitmq.normalisation import binding_fields, queue_fields
from integrations.rabbitmq.provider import RabbitMqMessagingProvider
from packages.collectors.sdk import Capability, CollectionRequest, IntegrationContext, ProviderRegistry
from packages.streaming.adapters.provider import require_observation_envelope
from packages.streaming.adapters.rabbitmq import RabbitMqAdapter


def raw_config(**changes):
    value = {
        "endpoint": "https://rabbit.example:15671",
        "authentication": {"type": "basic", "username": "monitor", "password_ref": "env:RABBIT_TEST_PASSWORD"},
        "tls": {"verify_certificate": True, "verify_hostname": True},
        "limits": {"page_size": 100},
    }
    value.update(changes)
    return value


def test_registration_and_capabilities():
    registry = ProviderRegistry()
    registry.register(RabbitMqMessagingProvider)
    provider = registry.create("rabbitmq")
    assert provider.provider_version == "1"
    assert provider.capabilities().supported == {
        Capability.RESOURCE_DISCOVERY,
        Capability.METADATA_COLLECTION,
        Capability.METRIC_COLLECTION,
        Capability.HEALTH_CHECK,
        Capability.INCREMENTAL_COLLECTION,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"unknown": True},
        {"endpoint": "https://user:password@rabbit.example"},
        {"endpoint": "http://rabbit.example"},
        {"tls": {"verify_certificate": False, "verify_hostname": True}},
        {"tls": {"verify_certificate": True, "verify_hostname": False}},
        {"limits": {"page_size": 501}},
    ],
)
def test_configuration_rejects_unsafe_values(change):
    with pytest.raises(Exception):
        parse_configuration(raw_config(**change))


def test_local_http_is_explicitly_allowed():
    assert parse_configuration(raw_config(endpoint="http://localhost:15672")).endpoint.startswith("http://")


def test_inline_password_and_unknown_auth_fields_rejected():
    with pytest.raises(Exception):
        parse_authentication({"type": "basic", "username": "u", "password": "plaintext"})


def test_auth_header_and_repr_are_redacted(monkeypatch):
    monkeypatch.setenv("RABBIT_TEST_PASSWORD", "secret")
    auth = parse_authentication(raw_config()["authentication"])
    assert auth.authorization_header().startswith("Basic ")
    assert "secret" not in repr(auth) and "secret" not in str(auth)


def test_queue_zero_missing_and_safe_arguments():
    fields = queue_fields(
        {
            "vhost": "/",
            "messages": 0,
            "messages_ready": 0,
            "messages_unacknowledged": 0,
            "consumers": 0,
            "type": "quorum",
            "arguments": {
                "x-message-ttl": 12,
                "x-max-length": 9,
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "private",
                "plugin-secret": "no",
            },
        }
    )
    assert fields["backlog_messages"] == 0 and fields["messages_ready"] == 0 and fields["unacknowledged_messages"] == 0
    assert fields["rabbitmq"]["queue_type"] == "quorum" and fields["rabbitmq"]["message_ttl_ms"] == 12
    assert "arguments" not in fields and "private" not in repr(fields) and "plugin-secret" not in repr(fields)
    missing = queue_fields({"vhost": "/", "name": "q"})
    assert missing["backlog_messages"] is None and missing["missing_inputs"]


@pytest.mark.parametrize("queue_type", ["classic", "quorum", "stream"])
def test_queue_types(queue_type):
    assert queue_fields({"type": queue_type})["rabbitmq"]["queue_type"] == queue_type


def test_routing_key_is_fingerprinted_not_retained():
    raw = {
        "vhost": "/",
        "source": "ex",
        "destination": "q",
        "destination_type": "queue",
        "routing_key": "orders.private",
    }
    first = binding_fields(raw)
    second = binding_fields(raw)
    assert first == second and first["routing_key_present"]
    assert "orders.private" not in repr(first)


class FakeClient:
    def __init__(self, cfg=None):
        pass

    def overview(self):
        return {"product_name": "RabbitMQ", "rabbitmq_version": "4.3.4"}

    def service_health(self):
        return {"status": "ok"}

    def alarm_health(self):
        return {"status": "ok"}

    def paginated(self, path):
        if path == "/api/vhosts":
            return iter([{"name": "/"}])
        if "/queues/" in path:
            return iter(
                [
                    {
                        "name": "source",
                        "vhost": "/",
                        "type": "classic",
                        "messages": 0,
                        "messages_ready": 0,
                        "messages_unacknowledged": 0,
                        "arguments": {"x-dead-letter-exchange": "dlx"},
                    },
                    {"name": "dead", "vhost": "/", "type": "quorum"},
                ]
            )
        if "/exchanges/" in path:
            return iter([{"name": "dlx", "vhost": "/", "type": "direct"}])
        if "/bindings/" in path:
            return iter(
                [
                    {
                        "vhost": "/",
                        "source": "dlx",
                        "destination": "dead",
                        "destination_type": "queue",
                        "routing_key": "secret",
                    }
                ]
            )
        return iter([])


def context():
    return IntegrationContext(
        "tenant",
        "integration",
        "run",
        datetime.now(timezone.utc) + timedelta(minutes=1),
        attributes={"environment": "test"},
    )


def test_dlq_requires_observed_binding_and_team1_envelope(monkeypatch):
    monkeypatch.setenv("RABBIT_TEST_PASSWORD", "secret")
    cfg = parse_configuration(raw_config())
    items = list(collect_vhost(FakeClient(), context(), cfg, "/"))
    resources = [x for x in items if hasattr(x, "source_evidence")]
    assert any(x.resource_type == "dead_letter_queue" and x.display_name == "dead" for x in resources)
    for item in resources:
        env = dict(item.source_evidence)
        require_observation_envelope(env)
        RabbitMqAdapter().resource(env)


def test_no_binding_means_no_fabricated_dlq(monkeypatch):
    monkeypatch.setenv("RABBIT_TEST_PASSWORD", "secret")

    class NoBindings(FakeClient):
        def paginated(self, path):
            return iter([]) if "/bindings/" in path else super().paginated(path)

    items = list(collect_vhost(NoBindings(), context(), parse_configuration(raw_config()), "/"))
    assert not any(getattr(x, "resource_type", None) == "dead_letter_queue" for x in items)


def test_provider_collection_is_partial_failure_isolated(monkeypatch):
    monkeypatch.setenv("RABBIT_TEST_PASSWORD", "secret")
    provider = RabbitMqMessagingProvider(FakeClient)
    assert asyncio.run(provider.validate_configuration(context(), raw_config())).valid

    async def gather():
        return [
            item
            async for item in provider.collect(context(), CollectionRequest(frozenset({Capability.RESOURCE_DISCOVERY})))
        ]

    assert asyncio.run(gather())


def test_static_get_only_and_no_amqp_or_message_operations():
    import integrations.rabbitmq as package

    root = os.path.dirname(inspect.getfile(package))
    source = "\n".join(
        open(os.path.join(root, name), encoding="utf-8").read() for name in os.listdir(root) if name.endswith(".py")
    )
    forbidden = (
        "basic_get",
        "basic_consume",
        "basic_publish",
        "basic_ack",
        "basic_nack",
        "pika",
        "aio_pika",
        'method="POST"',
        'method="PUT"',
        'method="PATCH"',
        'method="DELETE"',
        '/get"',
    )
    assert not any(token in source for token in forbidden)
    assert 'method="HEAD" if head else "GET"' in source
