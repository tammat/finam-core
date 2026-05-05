# src/finam_core/execution/real_execution.py

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class RealOrderResult:
    symbol: str
    side: str
    qty: float
    price: float | None
    status: str
    order_id: str | None = None
    reason: str | None = None
    raw: dict | None = None


class RealExecutionEngine:
    """
    Русский комментарий:
    Реальный execution-слой.
    Стратегия не имеет права вызывать этот класс напрямую.
    Только pipeline после RiskEngine.
    """

    def __init__(self, orders_client: Any) -> None:
        self.orders_client = orders_client
        self.mode = os.getenv("EXECUTION_MODE", "paper").strip().lower()

    def execute(self, intent: dict, market_state: dict | None = None) -> RealOrderResult:
        symbol = str(intent.get("symbol") or "")
        side = str(intent.get("side") or "")
        qty = float(intent.get("qty") or 0.0)
        price = intent.get("price")

        if not symbol or side not in ("BUY", "SELL") or qty <= 0:
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason="invalid_order_intent",
            )

        if self.mode == "real_dry_run":
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="DRY_RUN_ACCEPTED",
                order_id=f"dry_{symbol}_{side}_{qty}",
            )

        if self.mode != "real":
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason=f"unsupported_execution_mode={self.mode}",
            )

        if self.orders_client is None:
            return RealOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason="orders_client_not_configured",
            )

        result = self.orders_client.place_market_order(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
        )

        if isinstance(result, RealOrderResult):
            return result

        if isinstance(result, dict):
            return RealOrderResult(
                symbol=str(result.get("symbol") or symbol),
                side=str(result.get("side") or side),
                qty=float(result.get("qty") or qty),
                price=result.get("price", price),
                status=str(result.get("status") or "UNKNOWN"),
                order_id=result.get("order_id"),
                reason=result.get("reason"),
                raw=result,
            )

        return RealOrderResult(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            status=str(getattr(result, "status", "UNKNOWN")),
            order_id=getattr(result, "order_id", None),
            reason=getattr(result, "reason", None),
            raw={"result_type": type(result).__name__, "result_repr": repr(result)},
        )