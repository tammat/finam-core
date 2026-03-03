class EventJournal:
    """
    Append-only in-memory event store.
    Ready for PostgreSQL backend.
    """

    def __init__(self):
        self._events = []

    def append(self, event):
        self._events.append(event)

    def all_events(self):
        return list(self._events)

    def clear(self):
        self._events.clear()