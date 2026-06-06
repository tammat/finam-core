from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentAction(str, Enum):
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
class IntentSemanticsDecisionV2:
    side: str
    current_position: float
    requested_qty: float
    signed_qty: float
    resulting_position: float
    action: IntentAction
    reduce_only: bool
    opens_position: bool
    closes_position: bool
    reduces_position: bool
    adds_position: bool
    crosses_zero: bool


def classify_intent_semantics_v2(
    *,
    side: str,
    current_position: float,
    requested_qty: float,
) -> IntentSemanticsDecisionV2:
    """
    Русский комментарий:
    V2-семантика торгового намерения.

    Назначение:
    - явно различить OPEN/CLOSE/ADD/REDUCE;
    - снять двусмысленность SELL;
    - пока не подключается к execution и risk.
    """

    normalized_side = str(side or "").upper()
    pos = float(current_position or 0.0)
    qty = abs(float(requested_qty or 0.0))

    if qty <= 0 or normalized_side not in {"BUY", "SELL"}:
        return IntentSemanticsDecisionV2(
            side=normalized_side,
            current_position=pos,
            requested_qty=qty,
            signed_qty=0.0,
            resulting_position=pos,
            action=IntentAction.NOOP,
            reduce_only=False,
            opens_position=False,
            closes_position=False,
            reduces_position=False,
            adds_position=False,
            crosses_zero=False,
        )

    signed_qty = qty if normalized_side == "BUY" else -qty
    resulting = pos + signed_qty
    crosses_zero = (pos > 0 > resulting) or (pos < 0 < resulting)

    if normalized_side == "BUY":
        if pos == 0:
            action = IntentAction.OPEN_LONG
        elif pos > 0:
            action = IntentAction.ADD_LONG
        elif resulting < 0:
            action = IntentAction.REDUCE_SHORT
        else:
            action = IntentAction.CLOSE_SHORT

    else:
        if pos == 0:
            action = IntentAction.OPEN_SHORT
        elif pos < 0:
            action = IntentAction.ADD_SHORT
        elif resulting > 0:
            action = IntentAction.REDUCE_LONG
        else:
            action = IntentAction.CLOSE_LONG

    opens_position = action in {IntentAction.OPEN_LONG, IntentAction.OPEN_SHORT}
    closes_position = action in {IntentAction.CLOSE_LONG, IntentAction.CLOSE_SHORT}
    reduces_position = action in {IntentAction.REDUCE_LONG, IntentAction.REDUCE_SHORT}
    adds_position = action in {IntentAction.ADD_LONG, IntentAction.ADD_SHORT}
    reduce_only = action in {
        IntentAction.REDUCE_LONG,
        IntentAction.CLOSE_LONG,
        IntentAction.REDUCE_SHORT,
        IntentAction.CLOSE_SHORT,
    }

    return IntentSemanticsDecisionV2(
        side=normalized_side,
        current_position=pos,
        requested_qty=qty,
        signed_qty=signed_qty,
        resulting_position=resulting,
        action=action,
        reduce_only=reduce_only,
        opens_position=opens_position,
        closes_position=closes_position,
        reduces_position=reduces_position,
        adds_position=adds_position,
        crosses_zero=crosses_zero,
    )
