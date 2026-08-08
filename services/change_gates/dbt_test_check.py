def evaluate_run_results(document: dict | None) -> dict:
    if document is None:
        return {"status": "unknown", "evidence_status": "missing", "total": 0, "unavailable": 1}
    counts = {key: 0 for key in ("passed", "warning", "failed", "error", "skipped")}
    tests = []
    for item in document.get("results", []):
        if not str(item.get("unique_id", "")).startswith("test."):
            continue
        raw = str(item.get("status", "error")).lower()
        status = {"pass": "passed", "success": "passed", "warn": "warning", "fail": "failed"}.get(raw, raw)
        status = status if status in counts else "error"
        counts[status] += 1
        tests.append({"test": item.get("unique_id"), "status": status, "execution_time": item.get("execution_time")})
    status = "failed" if counts["failed"] or counts["error"] else "warning" if counts["warning"] else "passed"
    return {"status": status, "evidence_status": "available", "total": len(tests), **counts, "tests": tests}
