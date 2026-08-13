from __future__ import annotations

from urllib.parse import quote

from .evidence import metric, resource
from .normalisation import binding_fields, exchange_fields, queue_fields


def selected(value, includes, excludes):
    return value not in excludes and (not includes or value in includes)


def collect_vhosts(client, context, cfg):
    count = 0
    for raw in client.paginated("/api/vhosts"):
        name = raw.get("name")
        if not isinstance(name, str) or not selected(
            name, cfg.discovery["include_vhosts"], cfg.discovery["exclude_vhosts"]
        ):
            continue
        count += 1
        if count > cfg.limits["maximum_vhosts"]:
            raise RuntimeError("result_truncated")
        yield resource(
            context,
            "namespace",
            name,
            name,
            {key: raw.get(key) for key in ("default_queue_type", "protected_from_deletion", "tracing")},
        )


def collect_vhost(client, context, cfg, vhost):
    encoded = quote(vhost, safe="")
    queues = []
    for raw in client.paginated(f"/api/queues/{encoded}"):
        name = raw.get("name")
        if isinstance(name, str) and selected(name, cfg.discovery["include_queues"], cfg.discovery["exclude_queues"]):
            queues.append(raw)
    exchanges = list(client.paginated(f"/api/exchanges/{encoded}")) if cfg.discovery["include_exchanges"] else []
    bindings = list(client.paginated(f"/api/bindings/{encoded}")) if cfg.discovery["include_bindings"] else []
    dlq_names = set()
    if cfg.discovery["include_dead_letter_relationships"]:
        dlx = {
            raw.get("name"): raw.get("arguments", {}).get("x-dead-letter-exchange")
            for raw in queues
            if isinstance(raw.get("arguments"), dict)
        }
        for source_queue, exchange in dlx.items():
            for binding in bindings:
                if exchange and binding.get("source") == exchange and binding.get("destination_type") == "queue":
                    dlq_names.add(binding.get("destination"))
    for raw in queues[: cfg.limits["maximum_queues"]]:
        fields = queue_fields(raw)
        obs = resource(
            context,
            "dead_letter_queue" if raw.get("name") in dlq_names else "queue",
            raw["name"],
            vhost,
            fields,
            partial=bool(fields.get("missing_inputs")),
        )
        yield obs
        for native, canonical, aggregation in (
            ("messages", "rabbitmq.queue.messages", "gauge"),
            ("messages_ready", "rabbitmq.queue.messages_ready", "gauge"),
            ("messages_unacknowledged", "rabbitmq.queue.messages_unacknowledged", "gauge"),
        ):
            yield metric(obs, canonical, raw.get(native), aggregation=aggregation)
        for name, value in fields["message_statistics"].items():
            yield metric(obs, f"rabbitmq.queue.{name}", value, aggregation="counter")
    for raw in exchanges[: cfg.limits["maximum_exchanges"]]:
        if isinstance(raw.get("name"), str):
            yield resource(context, "exchange", raw["name"] or "(default)", vhost, exchange_fields(raw))
    for raw in bindings[: cfg.limits["maximum_bindings"]]:
        fields = binding_fields(raw)
        name = fields["routing_key_fingerprint"]
        yield resource(context, "exchange", f"binding:{name}", vhost, {"relationship_type": "binding", **fields})
