from datetime import datetime, timezone
from uuid import uuid4


class BaseEvent:
    def __init__(self, event_id=None, timestamp=None):
        self.event_id = event_id or str(uuid4())
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def __repr__(self):
        return f"{self.__class__.__name__}(event_id={self.event_id}, ts={self.timestamp})"