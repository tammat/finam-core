from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendGateDecision:
    allowed: bool
    reason: str


class TrendGateService:
    """
    Русский комментарий:
    Gate-фильтр направления сделки.

    BUY:
      разрешён только при bullish regime

    SELL:
      разрешён только при bearish regime
    """

    def allow_entry(
        self,
        symbol: str,
        side: str,
        expected_side: str | None,
    ) -> TrendGateDecision:

        if not expected_side:
            return TrendGateDecision(
                allowed=True,
                reason="trend_gate_no_expected_side",
            )

        actual = str(side or "").upper()
        expected = str(expected_side or "").upper()

        if actual != expected:
            return TrendGateDecision(
                allowed=False,
                reason=f"trend_block:expected={expected}:actual={actual}",
            )

        return TrendGateDecision(
            allowed=True,
            reason="trend_gate_ok",
        )
