# execution/execution_engine.py

from typing import Dict, Any
from src.infra.brokers.base import BrokerAdapter


class ExecutionEngine:

    def __init__(self, broker: BrokerAdapter):
        self._broker = broker

    def execute_signal(self, account_id: str, signal: Dict[str, Any]):
        return self._broker.place_order(
            account_id=account_id,
            symbol=signal["symbol"],
            side=signal["side"],
            quantity=signal["quantity"],
            order_type=signal.get("order_type", "MARKET"),
            price=signal.get("price"),
        )

    def cancel_order(self, account_id: str, order_id: str):
        return self._broker.cancel_order(account_id, order_id)