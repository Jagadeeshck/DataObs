def plan(desired, current):
    existing = {m.id: m for m in current}
    actions = []
    for item in desired["monitors"]:
        old = existing.get(item["id"])
        if old is None:
            action = "create"
        elif not item.get("etag"):
            action = "conflict"
        elif old.model_dump(mode="json") == item:
            action = "no_change"
        elif old.monitor_type.value != item.get("monitor_type") or old.target.model_dump(mode="json") != item.get(
            "target"
        ):
            action = "requires_baseline_reset"
        else:
            action = "update"
        actions.append({"monitor_id": item["id"], "action": action})
    return actions
