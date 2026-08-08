from ..normalisation import observation, safe, value

FIELDS = ("name", "slot_capacity", "ignore_idle_slots", "edition", "concurrency", "creation_time", "update_time")


def collect(client, context, cfg, admin, location):
    items = client.invoke("list_reservations", parent=f"projects/{admin}/locations/{location}")
    found = False
    for x in items:
        found = True
        rid = str(value(x, "name")).rsplit("/", 1)[-1]
        auto = value(x, "autoscale")
        yield observation(
            context,
            admin,
            location,
            "reservation",
            rid,
            rid,
            {**safe(x, FIELDS), "autoscaling_maximum_slots": value(auto, "max_slots")},
        )
    if not found:
        yield observation(
            context,
            admin,
            location,
            "reservation_state",
            "not_configured",
            "not_configured",
            {"state": "not_configured", "healthy": True},
        )
