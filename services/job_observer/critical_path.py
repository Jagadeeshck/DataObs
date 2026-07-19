def calculate(segments):
    """Longest dependency path over a DAG; cycles are reported as incomplete."""
    by_id = {x["id"]: x for x in segments}
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
        choices = [visit(d) for d in item.get("dependencies", []) if d in by_id]
        prior = max(choices, key=lambda x: x[0]) if choices else (0, [])
        visiting.remove(node)
        memo[node] = (prior[0] + item.get("duration_ms", 0), prior[1] + [node])
        return memo[node]

    best = max((visit(n) for n in by_id), default=(0, []), key=lambda x: x[0])
    return {
        "duration_ms": best[0],
        "segments": best[1],
        "confidence": 1 if not incomplete else 0.5,
        "incomplete_graph": incomplete,
    }
