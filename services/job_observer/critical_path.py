def calculate(segments):
    """Return an evidence-aware longest path without assuming a complete DAG."""
    by_id = {x.get("id") or x.get("entity_id"): x for x in segments}
    memo = {}
    visiting = set()
    incomplete = False

    def visit(node):
        nonlocal incomplete
        if node in memo:
            return memo[node]
        if node in visiting:
            incomplete = True
            return (0, [])
        visiting.add(node)
        item = by_id[node]
        dependencies = item.get("dependencies", [])
        if any(d not in by_id for d in dependencies):
            incomplete = True
        choices = [visit(d) for d in dependencies if d in by_id]
        prior = max(choices, key=lambda x: x[0]) if choices else (0, [])
        visiting.remove(node)
        duration = item.get("duration_ms")
        if duration is None or duration < 0:
            incomplete = True
            duration = max(0, duration or 0)
        memo[node] = (prior[0] + duration, prior[1] + [node])
        return memo[node]

    best = max((visit(n) for n in by_id), default=(0, []), key=lambda x: x[0])
    path = best[1]
    enriched = []
    for entity_id in path:
        item = by_id[entity_id]
        duration = max(0, item.get("duration_ms") or 0)
        enriched.append(
            {
                "entity_id": entity_id,
                "duration_ms": duration,
                "waiting_ms": max(0, item.get("waiting_ms") or 0),
                "execution_ms": max(0, item.get("execution_ms", duration) or 0),
                "slack_ms": max(0, item.get("slack_ms") or 0),
                "blocking_dependencies": item.get("dependencies", []),
                "evidence_ref": item.get("evidence_ref"),
            }
        )
    missing = ["complete dependency and timestamp evidence"] if incomplete else []
    return {
        "total_duration_ms": sum(max(0, x.get("duration_ms") or 0) for x in segments),
        "critical_path_duration_ms": best[0],
        "duration_ms": best[0],
        "segments": path,
        "segment_details": enriched,
        "confidence": 1.0 if not incomplete and segments else (0.5 if segments else 0.0),
        "incomplete_graph": incomplete,
        "missing_evidence": missing,
        "calculation_method": "longest_dependency_path_v1",
    }
