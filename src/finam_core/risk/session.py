# risk/session.py

from datetime import datetime, timezone

class TradingSessionProvider:
    def get_session_id(self) -> str:
        raise NotImplementedError


class DefaultSessionProvider(TradingSessionProvider):

    def __init__(self, tz=timezone.utc):
        self.tz = tz

    def get_session_id(self) -> str:
        return datetime.now(self.tz).date().isoformat()