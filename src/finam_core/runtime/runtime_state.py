from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RuntimeWorkerState:
    symbol: str
    enabled: bool
    status: str
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    last_error: Optional[str] = None
