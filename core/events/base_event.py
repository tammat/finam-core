from dataclasses import dataclass
from datetime import datetime


@dataclass
class BaseEvent:
    event_id: str
    timestamp: datetime