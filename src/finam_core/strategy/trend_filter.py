from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendFilterDecision:
    allowed: bool
    expected: str
    actual: str
    reason: str


class TrendFilter:
    """Русский комментарий: фильтр направления сделки против ожидаемого тренда."""

    def check(
        self,
        *,
        expected: str | None,
        actual: str | None,
    ) -> TrendFilterDecision:
        exp = (expected or "").upper()
        act = (actual or "").upper()

        if not exp or not act:
            return TrendFilterDecision(True, exp, act, "no_trend_filter")

        if exp != act:
            return TrendFilterDecision(False, exp, act, "trend_mismatch")

        return TrendFilterDecision(True, exp, act, "trend_match")
