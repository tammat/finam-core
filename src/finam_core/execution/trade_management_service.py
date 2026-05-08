from __future__ import annotations

import logging
import os

from finam_core.execution.auto_breakeven_manager import (
    AutoBreakevenManager,
    BreakevenRule,
)
from finam_core.execution.stop_replacement_engine import (
    StopReplacementEngine,
    StopReplacementRequest,
)

LOG = logging.getLogger(__name__)


class TradeManagementService:
    def __init__(self, orders_client=None):
        self.enabled = os.getenv("TRADE_MANAGEMENT_ENABLED", "1") == "1"
        self.live_replace = os.getenv("STOP_REPLACE_LIVE", "0") == "1"

        self.be = AutoBreakevenManager([
            BreakevenRule(symbol="BRM6", entry_price=98.32),
            BreakevenRule(symbol="NGK6", entry_price=2.841),
        ])

        self.stop_replacer = StopReplacementEngine(
            orders_client=orders_client,
            dry_run=not self.live_replace,
        )

    def on_take_profit_fill(self, symbol: str, tp_index: int, qty=None, side=None, stop_order_id=None):
        if not self.enabled:
            return None

        action = self.be.on_take_profit_fill(symbol=symbol, tp_index=tp_index)
        if action is None:
            return None

        req = StopReplacementRequest(
            symbol=action.symbol,
            stop_order_id=stop_order_id or action.stop_order_id,
            new_stop=action.new_stop,
            qty=qty,
            side=side,
            reason=action.reason,
        )

        result = self.stop_replacer.replace_stop(req)

        print(
            "TRADE_MANAGEMENT_STOP_REPLACE "
            f"symbol={result.symbol} "
            f"new_stop={result.new_stop} "
            f"status={result.status} "
            f"live={self.live_replace} "
            f"reason={result.reason}",
            flush=True,
        )

        return result
