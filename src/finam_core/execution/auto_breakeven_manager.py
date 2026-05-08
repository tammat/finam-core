from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BreakevenRule:
    symbol: str
    entry_price: float
    stop_order_id: str | None = None
    offset: float = 0.0


@dataclass(frozen=True)
class BreakevenAction:
    symbol: str
    new_stop: float
    reason: str
    stop_order_id: str | None = None


class AutoBreakevenManager:
    """
    Moves protective stop to entry after TP1 fill.
    Safe by design: returns an action, does not send real orders itself.
    """

    def __init__(self, rules: list[BreakevenRule]):
        self.rules = {r.symbol: r for r in rules}
        self.triggered: set[str] = set()

    def on_take_profit_fill(self, symbol: str, tp_index: int) -> BreakevenAction | None:
        if tp_index != 1:
            return None

        if symbol in self.triggered:
            return None

        rule = self.rules.get(symbol)
        if rule is None:
            return None

        self.triggered.add(symbol)

        return BreakevenAction(
            symbol=symbol,
            new_stop=round(rule.entry_price + rule.offset, 6),
            stop_order_id=rule.stop_order_id,
            reason="TP1 filled: move protective stop to breakeven",
        )
