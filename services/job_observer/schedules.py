def schedule_state(expected_at, started_at, grace_seconds, confidence):
    if confidence < 0.8:
        return {"state": "unknown", "confidence": confidence, "reason": "insufficient schedule evidence"}
    if started_at is None:
        return {"state": "missing", "confidence": confidence}
    delay = max(0, (started_at - expected_at).total_seconds())
    return {"state": "late" if delay > grace_seconds else "on_time", "delay_seconds": delay, "confidence": confidence}
