from __future__ import annotations

from dataclasses import dataclass

from finam_core.analytics.entry_exit_optimizer import Bar


@dataclass(frozen=True)
class PendingEntryDecisionV1:
    status: str
    entry_price: float | None
    reason: str


def evaluate_pending_entry_v1(*, mode: str, side: str, signal_price: float,
                              atr: float, bars: list[Bar]) -> PendingEntryDecisionV1:
    """Evaluate only completed bars after a persisted Paper signal."""
    if mode not in {"CONFIRM_1", "RETEST_3"} or signal_price <= 0 or atr <= 0:
        return PendingEntryDecisionV1("CANCELLED", None, "INVALID_PENDING_ENTRY")
    if not bars:
        return PendingEntryDecisionV1("PENDING", None, "WAIT_COMPLETED_BAR")
    direction = 1 if side.upper() in {"LONG", "BUY"} else -1
    if mode == "CONFIRM_1":
        bar = bars[0]
        if direction * (bar.close - signal_price) > 0:
            return PendingEntryDecisionV1("READY", bar.close, "CONFIRMATION_CLOSE")
        return PendingEntryDecisionV1("CANCELLED", None, "CONFIRMATION_FAILED")

    for bar in bars[:3]:
        favourable = (bar.high - signal_price if direction > 0
                      else signal_price - bar.low)
        if favourable > atr * 0.70:
            return PendingEntryDecisionV1("CANCELLED", None, "RUNAWAY_OR_AMBIGUOUS_BAR")
        touched = (bar.low <= signal_price + atr * 0.20 if direction > 0
                   else bar.high >= signal_price - atr * 0.20)
        confirmed = direction * (bar.close - signal_price) >= 0
        if touched and confirmed:
            return PendingEntryDecisionV1("READY", bar.close, "RETEST_CONFIRMED_CLOSE")
    if len(bars) >= 3:
        return PendingEntryDecisionV1("CANCELLED", None, "RETEST_NOT_CONFIRMED_IN_3_BARS")
    return PendingEntryDecisionV1("PENDING", None, "WAIT_RETEST_BAR")
