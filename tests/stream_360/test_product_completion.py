import pytest

from services.product_query.stream_actions import ActionStore
from services.product_query.stream_comparison import compare_samples
from services.product_query.stream_links import kibana_link
from services.product_query.stream_pagination import CursorCodec, CursorState, InvalidCursor
from services.product_query.stream_sse import EventReplay


def test_comparison_uses_measured_samples_and_reports_missing_evidence():
    result = compare_samples([{"total_lag": 30}], [{"total_lag": 20}])
    assert result["sample_count"] == 2
    assert result["deltas"][0]["absolute_delta"] == 10
    assert result["deltas"][0]["percentage_delta"] == 50
    assert "latency_p99" in result["missing_evidence"]


def test_action_is_tenant_bound_idempotent_and_allowlisted():
    store = ActionStore()
    request = dict(
        tenant="acme",
        environment="prod",
        target_id="sink",
        action="restart_failed_connector",
        reason="failed task needs recovery",
        requester="operator",
        idempotency_key="key-1",
        eligible=True,
    )
    first = store.request(**request)
    assert first == store.request(**request)
    assert first["state"] == "awaiting_approval"
    assert store.list("other", "prod", "sink") == []
    with pytest.raises(ValueError, match="allowlisted"):
        store.request(**(request | {"action": "broker_restart", "idempotency_key": "key-2"}))


def test_kibana_links_reject_ssrf_and_query_injection():
    link = kibana_link(
        "https://kibana.example.test", "discover", tenant="acme", environment="prod", resource_id="orders & returns"
    )
    assert link.startswith("https://kibana.example.test/app/discover?")
    assert "orders+%26+returns" in link
    with pytest.raises(ValueError):
        kibana_link("http://169.254.169.254", "discover", tenant="a", environment="p", resource_id="x")
    with pytest.raises(ValueError):
        kibana_link("https://kibana.example.test", "https://evil.test", tenant="a", environment="p", resource_id="x")


def test_sse_payload_and_replay_are_tenant_isolated():
    replay = EventReplay(2)
    event = replay.publish("acme", "prod", "stream.resource.updated", {"resource_id": "orders", "password": "sentinel"})
    assert "password" not in event.payload
    assert replay.replay("other", "prod") == []
    assert replay.replay("acme", "prod")[0].event_id == event.event_id


def test_cursor_is_bound_to_route_resource_sort_and_rotated_key():
    old = CursorCodec("old-secret-with-enough-bytes")
    cursor = old.encode(
        CursorState(["orders", "1"]),
        tenant="acme",
        environment="prod",
        filters={"health": "critical"},
        route="streams",
        resource="streams",
        sort={"maximum_lag": "desc"},
    )
    rotated = CursorCodec("new-secret-with-enough-bytes", previous_secrets=["old-secret-with-enough-bytes"])
    assert (
        rotated.decode(
            cursor,
            tenant="acme",
            environment="prod",
            filters={"health": "critical"},
            route="streams",
            resource="streams",
            sort={"maximum_lag": "desc"},
        ).sort[0]
        == "orders"
    )
    with pytest.raises(InvalidCursor, match="route"):
        rotated.decode(
            cursor,
            tenant="acme",
            environment="prod",
            filters={"health": "critical"},
            route="consumer-groups",
            resource="consumer_groups",
            sort={"maximum_lag": "desc"},
        )
