# execution/order_model.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import uuid4


@dataclass
class Order:

    # --- Core identity ---
    order_id: str
    symbol: str
    side: str                # BUY / SELL / LONG / SHORT
    qty: float
    price: float
    signal_event_id: str
    created_ts: datetime

    # --- Execution state ---
    status: str = "NEW"      # NEW / PARTIALLY_FILLED / FILLED / CANCELLED
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0

    # --- Partial fills ---
    fills: List = field(default_factory=list)

    # --- Lifecycle ---
    updated_ts: Optional[datetime] = None

    # ------------------------------------------------------------
    # ------------------- Execution Logic ------------------------
    # ------------------------------------------------------------

    def add_fill(self, fill):
        """
        Adds partial fill and recalculates avg price.
        """

        self.fills.append(fill)

        previous_value = self.avg_fill_price * self.filled_qty
        new_value = fill.price * fill.qty

        self.filled_qty += fill.qty

        if self.filled_qty > 0:
            self.avg_fill_price = (previous_value + new_value) / self.filled_qty

        # Update status
        if self.filled_qty < self.qty:
            self.status = "PARTIALLY_FILLED"
        else:
            self.status = "FILLED"

        self.updated_ts = fill.timestamp

    # ------------------------------------------------------------
    # ------------------- Helpers --------------------------------
    # ------------------------------------------------------------

    @property
    def remaining_qty(self) -> float:
        return max(self.qty - self.filled_qty, 0.0)

    @property
    def is_filled(self) -> bool:
        return self.status == "FILLED"

    @property
    def notional(self) -> float:
        return self.qty * self.price

    @staticmethod
    def create_from_signal(signal_event, qty: float = 1.0):
        return Order(
            order_id=str(uuid4()),
            symbol=signal_event.symbol,
            side=signal_event.signal_type,
            qty=qty,
            price=getattr(signal_event, "price", 0.0),
            signal_event_id=signal_event.event_id,
            created_ts=signal_event.timestamp,
        )