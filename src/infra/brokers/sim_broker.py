from datetime import datetime,UTC
from uuid import uuid4
from typing import Any

from src.infra.brokers.base import BrokerAdapter
from src.core.events.fill_event import FillEvent


class SimBrokerAdapter(BrokerAdapter):

    def __init__(self, price_resolver=None):
        self.price_resolver = price_resolver
        self._running = False

    # --- lifecycle ---

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    # --- market data ---

    def subscribe_quotes(self, symbols: list[str]):
        return {"status": "SUBSCRIBED", "symbols": symbols}

    def unsubscribe_quotes(self, symbols: list[str]):
        return {"status": "UNSUBSCRIBED", "symbols": symbols}

    # --- account info ---

    def get_accounts(self):
        return [{"account_id": "SIM_ACCOUNT"}]

    def get_positions(self, account_id: str):
        return []

    def get_orders(self, account_id: str):
        return []

    # --- trading ---

    def place_order(
        self,
        account_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> FillEvent:

        resolved_price = (
            self.price_resolver(symbol)
            if self.price_resolver
            else price or 0.0
        )

        return FillEvent(
            event_id=str(uuid4()),
            fill_id=str(uuid4()),
            order_id=str(uuid4()),
            symbol=symbol,
            side=side,
            qty=quantity,
            price=float(resolved_price),
            commission=0.0,
            timestamp=None,  # BaseEvent сам поставит UTC
        )
    def cancel_order(self, account_id: str, order_id: str) -> dict[str, Any]:
        return {"status": "CANCELLED", "order_id": order_id}