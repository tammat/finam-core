class Event:
    """Base class for all events."""
    pass


# ---------- Strategy Layer ----------

class StrategySignalEvent(Event):
    def __init__(self, symbol: str, side: str, qty: float, price: float):
        self.symbol = symbol
        self.side = side
        self.qty = float(qty)
        self.price = float(price)


# ---------- Order Lifecycle ----------

class OrderCreateRequestedEvent(Event):
    def __init__(self, symbol: str, side: str, qty: float, price: float):
        self.symbol = symbol
        self.side = side
        self.qty = float(qty)
        self.price = float(price)


class RiskCheckRequestedEvent(Event):
    def __init__(self, order):
        self.order = order


class RiskApprovedEvent(Event):
    def __init__(self, order):
        self.order = order


class RiskRejectedEvent(Event):
    def __init__(self, order, reason: str):
        self.order = order
        self.reason = reason


# ---------- Execution Layer ----------

class ExecutionEvent(Event):
    def __init__(self, fill):
        self.fill = fill


# ---------- Portfolio Layer ----------

class PortfolioUpdatedEvent(Event):
    def __init__(self, state):
        self.state = state