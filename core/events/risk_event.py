from .base_event import BaseEvent


class RiskEvent(BaseEvent):
    def __init__(self, approved: bool, reason: str, symbol: str):
        super().__init__()
        self.approved = approved
        self.reason = reason
        self.symbol = symbol

    def __repr__(self):
        return (
            f"RiskEvent("
            f"event_id={self.event_id}, "
            f"symbol={self.symbol}, "
            f"approved={self.approved}, "
            f"reason={self.reason})"
        )