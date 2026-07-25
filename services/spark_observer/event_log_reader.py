import json
from pathlib import Path


def read(path, checkpoint=0, max_events=10000):
    p = Path(path).resolve()
    if not p.is_file():
        raise ValueError("event log must be an existing file")
    events = []
    with p.open() as stream:
        for number, line in enumerate(stream):
            if number < checkpoint:
                continue
            if len(events) >= max_events:
                break
            events.append(json.loads(line))
    return events, checkpoint + len(events)
