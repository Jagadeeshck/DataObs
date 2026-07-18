def deterministic_retry_delay(attempt:int, base_seconds:int=5)->int:
    return min(base_seconds * (2 ** max(0, attempt-1)), 300)
