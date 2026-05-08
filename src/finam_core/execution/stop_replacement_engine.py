from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StopReplacementRequest:
    symbol: str
    stop_order_id: str | None
    new_stop: float
    qty: float | None = None
    side: str | None = None
    reason: str = "stop replacement"


@dataclass(frozen=True)
class StopReplacementResult:
    success: bool
    symbol: str
    new_stop: float
    status: str
    reason: str
    raw: Any | None = None


class StopReplacementEngine:
    """
    Safe stop replacement layer.

    Does not decide when to move stops.
    It only executes an already-approved replacement request.
    """

    def __init__(self, orders_client, dry_run: bool = True):
        self.orders_client = orders_client
        self.dry_run = dry_run
        self._seen: set[tuple[str, str | None, float]] = set()

    def replace_stop(self, req: StopReplacementRequest) -> StopReplacementResult:
        key = (req.symbol, req.stop_order_id, round(float(req.new_stop), 6))

        if key in self._seen:
            return StopReplacementResult(
                success=True,
                symbol=req.symbol,
                new_stop=req.new_stop,
                status="duplicate_ignored",
                reason=req.reason,
            )

        self._seen.add(key)

        if self.dry_run:
            return StopReplacementResult(
                success=True,
                symbol=req.symbol,
                new_stop=req.new_stop,
                status="dry_run",
                reason=req.reason,
            )

        if req.stop_order_id:
            cancel = getattr(self.orders_client, "cancel_order", None)
            if not callable(cancel):
                return StopReplacementResult(
                    success=False,
                    symbol=req.symbol,
                    new_stop=req.new_stop,
                    status="missing_cancel_order",
                    reason=req.reason,
                )
            cancel(req.stop_order_id)

        place = getattr(self.orders_client, "place_stop_order", None)
        if not callable(place):
            return StopReplacementResult(
                success=False,
                symbol=req.symbol,
                new_stop=req.new_stop,
                status="missing_place_stop_order",
                reason=req.reason,
            )

        raw = place(
            symbol=req.symbol,
            side=req.side,
            qty=req.qty,
            stop_price=req.new_stop,
            reason=req.reason,
        )

        return StopReplacementResult(
            success=True,
            symbol=req.symbol,
            new_stop=req.new_stop,
            status="replaced",
            reason=req.reason,
            raw=raw,
        )
