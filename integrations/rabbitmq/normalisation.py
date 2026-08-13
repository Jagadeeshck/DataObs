from __future__ import annotations

from .evidence import fingerprint


def queue_fields(raw):
    arguments = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else {}
    queue_type = raw.get("type", arguments.get("x-queue-type", "unknown"))
    if queue_type not in {"classic", "quorum", "stream"}:
        queue_type = "unknown"
    fields = {
        "rabbitmq": {
            "vhost": raw.get("vhost"),
            "durable": raw.get("durable"),
            "exclusive": raw.get("exclusive"),
            "auto_delete": raw.get("auto_delete"),
            "queue_type": queue_type,
            "message_ttl_ms": arguments.get("x-message-ttl"),
            "max_length": arguments.get("x-max-length"),
            "dead_letter_exchange": arguments.get("x-dead-letter-exchange"),
        },
        "consumer_count": raw.get("consumers"),
        "backlog_messages": raw.get("messages"),
        "messages_ready": raw.get("messages_ready"),
        "unacknowledged_messages": raw.get("messages_unacknowledged"),
        "dead_letter_routing_key_present": "x-dead-letter-routing-key" in arguments,
    }
    stats = raw.get("message_stats") if isinstance(raw.get("message_stats"), dict) else {}
    fields["message_statistics"] = {
        key: stats[key]
        for key in ("publish", "deliver", "deliver_no_ack", "deliver_get", "ack", "redeliver")
        if key in stats
    }
    missing = [key for key in ("messages", "messages_ready", "messages_unacknowledged") if key not in raw]
    if missing:
        fields["missing_inputs"] = missing
    return fields


def exchange_fields(raw):
    return {key: raw.get(key) for key in ("type", "durable", "auto_delete", "internal")}


def binding_fields(raw):
    vhost, source, destination = (str(raw.get(k, "")) for k in ("vhost", "source", "destination"))
    destination_type = str(raw.get("destination_type", "unknown"))
    routing_key = str(raw.get("routing_key", ""))
    return {
        "source_exchange": source,
        "destination": destination,
        "destination_type": destination_type,
        "routing_key_present": bool(routing_key),
        "routing_key_fingerprint": fingerprint(vhost, source, destination, destination_type, routing_key),
    }
