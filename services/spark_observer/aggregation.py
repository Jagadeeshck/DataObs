def summarize(tasks, limit=100):
    total = len(tasks)
    sample = tasks[:limit]
    return {
        "total": total,
        "sampled": len(sample),
        "complete": total <= limit,
        "failed": sum(1 for x in tasks if x.get("failed")),
        "sample": sample,
    }
