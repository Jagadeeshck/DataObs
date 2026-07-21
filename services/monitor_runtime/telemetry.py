from collections import Counter


class RuntimeTelemetry:
    """In-process bounded-label telemetry adapter."""

    def __init__(self):
        self.counters = Counter()

    def increment(self, name: str, *, outcome: str = "ok"):
        self.counters[(name, outcome)] += 1
