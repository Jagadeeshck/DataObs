MAP = {
    "START": "running",
    "RUNNING": "running",
    "COMPLETE": "success",
    "FAIL": "failed",
    "ABORT": "aborted",
    "OTHER": "unknown",
}


def normalized_state(source_state):
    return MAP.get(source_state, "unknown")
