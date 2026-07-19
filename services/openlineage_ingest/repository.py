class InMemoryEventRepository:
    def __init__(self):
        self.events = {}
        self.dead_letters = {}

    def append(self, event):
        created = event["event_id"] not in self.events
        self.events.setdefault(event["event_id"], event)
        return created

    def dead_letter(self, event_id, record):
        self.dead_letters[event_id] = record
