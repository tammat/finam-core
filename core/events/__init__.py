import uuid
from datetime import datetime


class EventBase:
    def __init__(self, stream: str = "portfolio-1"):
        self.stream = stream
        self.id = uuid.uuid4()
        self.created_at = datetime.utcnow()

    @property
    def type(self):
        return self.__class__.__name__

    def to_dict(self):
        return {
            k: (
                str(v) if isinstance(v, uuid.UUID)
                else v.isoformat() if hasattr(v, "isoformat")
                else v
            )
            for k, v in self.__dict__.items()
        }


# =========================================================
# Strategy
# =========================================================

class StrategySignalEvent(EventBase):
    def __init__(self, symbol, side, qty, price):
        super().__init__(stream="portfolio-1")
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price


# =========================================================
# Order
# =========================================================

class OrderCreateRequestedEvent(EventBase):
    def __init__(self, symbol, side, qty, price):
        super().__init__()
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price


class OrderCreatedEvent(EventBase):
    def __init__(self, symbol, side, qty, price):
        super().__init__()
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price


# =========================================================
# Risk
# =========================================================

class RiskCheckRequestedEvent(EventBase):
    def __init__(self, symbol, side, qty, price):
        super().__init__()
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price


class RiskApprovedEvent(EventBase):
    def __init__(self, symbol, side, qty, price):
        super().__init__()
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price


class RiskRejectedEvent(EventBase):
    def __init__(self, symbol, side, qty, price, reason=""):
        super().__init__()
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price
        self.reason = reason


# =========================================================
# Execution
# =========================================================

class ExecutionEvent(EventBase):
    def __init__(self, symbol, side, qty, price, fill_id=None):
        super().__init__()
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.price = price
        self.fill_id = fill_id


# =========================================================
# Portfolio
# =========================================================

class PortfolioUpdatedEvent(EventBase):
    def __init__(self, state: dict):
        super().__init__()
        self.state = state