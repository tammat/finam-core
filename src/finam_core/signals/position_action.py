from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PositionAction(str, Enum):
    OPEN_LONG = "OPEN_LONG"
    ADD_LONG = "ADD_LONG"
    REDUCE_LONG = "REDUCE_LONG"
    CLOSE_LONG = "CLOSE_LONG"
    OPEN_SHORT = "OPEN_SHORT"
    ADD_SHORT = "ADD_SHORT"
    REDUCE_SHORT = "REDUCE_SHORT"
    CLOSE_SHORT = "CLOSE_SHORT"
    NOOP = "NOOP"


@dataclass(frozen=True, slots=True)
class PositionActionDecision:
    side: str
    current_position: float
    quantity: float
    signed_quantity: float
    resulting_position: float
    action: PositionAction
    crosses_zero: bool


def classify_position_action(
    *,
    side: str,
    current_position: float,
    quantity: float,
) -> PositionActionDecision:
    """
    Русский комментарий:
    Классифицирует BUY/SELL относительно текущей позиции.

    Не отправляет заявки.
    Не меняет риск.
    Не меняет execution.
    Только определяет явный position_action.
    """

    normalized_side = str(side or "").upper()
    qty = abs(float(quantity or 0.0))
    pos = float(current_position or 0.0)

    if qty <= 0 or normalized_side not in {"BUY", "SELL"}:
        return PositionActionDecision(
            side=normalized_side,
            current_position=pos,
            quantity=qty,
            signed_quantity=0.0,
            resulting_position=pos,
            action=PositionAction.NOOP,
            crosses_zero=False,
        )

    signed_qty = qty if normalized_side == "BUY" else -qty
    resulting = pos + signed_qty
    crosses_zero = (pos > 0 > resulting) or (pos < 0 < resulting)

    if normalized_side == "BUY":
        if pos == 0:
            action = PositionAction.OPEN_LONG
        elif pos > 0:
            action = PositionAction.ADD_LONG
        elif resulting < 0:
            action = PositionAction.REDUCE_SHORT
        elif resulting == 0:
            action = PositionAction.CLOSE_SHORT
        else:
            action = PositionAction.CLOSE_SHORT

    else:
        if pos == 0:
            action = PositionAction.OPEN_SHORT
        elif pos < 0:
            action = PositionAction.ADD_SHORT
        elif resulting > 0:
            action = PositionAction.REDUCE_LONG
        elif resulting == 0:
            action = PositionAction.CLOSE_LONG
        else:
            action = PositionAction.CLOSE_LONG

    return PositionActionDecision(
        side=normalized_side,
        current_position=pos,
        quantity=qty,
        signed_quantity=signed_qty,
        resulting_position=resulting,
        action=action,
        crosses_zero=crosses_zero,
    )
