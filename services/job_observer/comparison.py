def compare(base, target):
    fields = ("duration_ms", "queue_delay_ms", "schedule_delay_ms", "input_records", "output_records")
    deltas = {}
    percentages = {}
    for f in fields:
        a, b = base.get(f), target.get(f)
        deltas[f] = None if a is None or b is None else b - a
        percentages[f] = None if a in (None, 0) or b is None else (b - a) / a * 100
    old = set(base.get("entities", []))
    new = set(target.get("entities", []))
    return {
        "deltas": deltas,
        "percentage_deltas": percentages,
        "new_entities": sorted(new - old),
        "removed_entities": sorted(old - new),
    }
