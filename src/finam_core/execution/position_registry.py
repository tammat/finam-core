from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ManagedPosition:
    symbol: str
    side: str
    qty: float
    entry_price: float
    stop_order_id: str | None = None
    tp1_order_id: str | None = None
    tp2_order_id: str | None = None
    breakeven_done: bool = False
    tp1_done: bool = False
    tp2_done: bool = False


class PositionRegistry:
    """
    In-memory registry for managed positions.

    Safe by design:
    - idempotent state transitions
    - no broker calls
    - suitable for replay/recovery tests
    """

    def __init__(self):
        self._positions: dict[str, ManagedPosition] = {}

    def register_position(self, pos: ManagedPosition) -> ManagedPosition:
        self._positions[pos.symbol] = pos
        return pos

    def get(self, symbol: str) -> ManagedPosition | None:
        return self._positions.get(symbol)

    def all(self) -> list[ManagedPosition]:
        return list(self._positions.values())

    def remove(self, symbol: str) -> ManagedPosition | None:
        return self._positions.pop(symbol, None)

    def mark_tp1_filled(self, symbol: str) -> ManagedPosition | None:
        pos = self.get(symbol)
        if pos is None:
            return None
        if pos.tp1_done:
            return pos
        updated = replace(pos, tp1_done=True)
        self._positions[symbol] = updated
        return updated

    def mark_tp2_filled(self, symbol: str) -> ManagedPosition | None:
        pos = self.get(symbol)
        if pos is None:
            return None
        if pos.tp2_done:
            return pos
        updated = replace(pos, tp2_done=True)
        self._positions[symbol] = updated
        return updated

    def mark_breakeven_done(self, symbol: str, stop_order_id: str | None = None) -> ManagedPosition | None:
        pos = self.get(symbol)
        if pos is None:
            return None
        if pos.breakeven_done and (stop_order_id is None or pos.stop_order_id == stop_order_id):
            return pos
        updated = replace(
            pos,
            breakeven_done=True,
            stop_order_id=stop_order_id if stop_order_id is not None else pos.stop_order_id,
        )
        self._positions[symbol] = updated
        return updated

    def update_stop(self, symbol: str, stop_order_id: str | None) -> ManagedPosition | None:
        pos = self.get(symbol)
        if pos is None:
            return None
        updated = replace(pos, stop_order_id=stop_order_id)
        self._positions[symbol] = updated
        return updated
