from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgShortBlockDecisionV1:
    symbol: str
    side: str
    position: float
    quantity: float
    allowed: bool
    reason: str
    action: str


class NgShortBlockPolicyV1:
    """
    Русский комментарий:
    Блокирует открытие/наращивание NG short после отрицательной статистики.
    Закрытие или сокращение long через SELL разрешается.
    """

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        position: float,
        quantity: float,
    ) -> NgShortBlockDecisionV1:
        symbol_u = str(symbol or "").upper()
        side_u = str(side or "").upper()
        pos = float(position or 0.0)
        qty = abs(float(quantity or 0.0))

        if not symbol_u.startswith("NG"):
            return NgShortBlockDecisionV1(symbol, side_u, pos, qty, True, "not_ng_symbol", "PASS")

        if side_u != "SELL":
            return NgShortBlockDecisionV1(symbol, side_u, pos, qty, True, "not_sell", "PASS")

        if pos > 0:
            action = "CLOSE_LONG" if qty >= pos else "REDUCE_LONG"
            return NgShortBlockDecisionV1(symbol, side_u, pos, qty, True, "ng_sell_reduces_or_closes_long", action)

        if pos == 0:
            return NgShortBlockDecisionV1(symbol, side_u, pos, qty, False, "ng_open_short_blocked_negative_edge", "OPEN_SHORT")

        return NgShortBlockDecisionV1(symbol, side_u, pos, qty, False, "ng_add_short_blocked_negative_edge", "ADD_SHORT")
