# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Iterable


@dataclass(frozen=True)
class VolatilityCandidate:
    """Русский комментарий: результат отбора инструмента для intraday/swing watchlist."""

    symbol: str
    horizon: str
    score: float
    spread_pct: float
    range_pct: float
    turnover: float
    rvol: float
    impulse_score: float
    trend_score: float
    regime: str
    reason: str


class VolatilityScanner:
    """
    Русский комментарий:
    Сканер инструментов для intraday и swing.
    Не отправляет заявки и не принимает торговых решений.
    """

    def __init__(
        self,
        *,
        min_turnover: float = 300_000_000.0,
        max_spread_pct: float = 0.0025,
        min_range_pct_intraday: float = 0.012,
        min_range_pct_swing: float = 0.025,
        min_rvol_intraday: float = 1.2,
        min_rvol_swing: float = 0.8,
    ) -> None:
        self.min_turnover = float(min_turnover)
        self.max_spread_pct = float(max_spread_pct)
        self.min_range_pct_intraday = float(min_range_pct_intraday)
        self.min_range_pct_swing = float(min_range_pct_swing)
        self.min_rvol_intraday = float(min_rvol_intraday)
        self.min_rvol_swing = float(min_rvol_swing)

    def scan_intraday(self, rows: Iterable[dict[str, Any]], *, top_n: int = 10) -> list[VolatilityCandidate]:
        candidates = [self._score_row(row, horizon="intraday") for row in rows]
        passed = [item for item in candidates if item.score > 0]
        return sorted(passed, key=lambda item: item.score, reverse=True)[:top_n]

    def scan_swing(self, rows: Iterable[dict[str, Any]], *, top_n: int = 10) -> list[VolatilityCandidate]:
        candidates = [self._score_row(row, horizon="swing") for row in rows]
        passed = [item for item in candidates if item.score > 0]
        return sorted(passed, key=lambda item: item.score, reverse=True)[:top_n]

    def scan(self, rows: Iterable[dict[str, Any]], *, top_n: int = 10) -> dict[str, list[VolatilityCandidate]]:
        rows_list = list(rows)
        return {
            "intraday": self.scan_intraday(rows_list, top_n=top_n),
            "swing": self.scan_swing(rows_list, top_n=top_n),
        }

    def _score_row(self, row: dict[str, Any], *, horizon: str) -> VolatilityCandidate:
        symbol = str(row.get("symbol") or "")
        last = self._num(row.get("last"), 0.0)
        high = self._num(row.get("high"), last)
        low = self._num(row.get("low"), last)
        open_price = self._num(row.get("open"), last)
        close = self._num(row.get("close"), last)
        bid = self._num(row.get("bid"), 0.0)
        ask = self._num(row.get("ask"), 0.0)
        volume = self._num(row.get("volume"), 0.0)
        avg_volume = self._num(row.get("avg_volume"), 0.0)
        turnover = self._num(row.get("turnover"), close * volume if close > 0 else 0.0)

        spread_pct = self._spread_pct(bid=bid, ask=ask, last=last or close)
        range_pct = self._range_pct(high=high, low=low, base=close or last)
        rvol = self._rvol(volume=volume, avg_volume=avg_volume)
        trend_score = self._trend_score(open_price=open_price, close=close or last)
        impulse_score = self._impulse_score(range_pct=range_pct, rvol=rvol, trend_score=trend_score)
        regime = self._regime(range_pct=range_pct, rvol=rvol, trend_score=trend_score)

        ok, reason = self._passes_filters(
            horizon=horizon,
            symbol=symbol,
            turnover=turnover,
            spread_pct=spread_pct,
            range_pct=range_pct,
            rvol=rvol,
        )

        if not ok:
            return VolatilityCandidate(
                symbol=symbol,
                horizon=horizon,
                score=0.0,
                spread_pct=spread_pct,
                range_pct=range_pct,
                turnover=turnover,
                rvol=rvol,
                impulse_score=impulse_score,
                trend_score=trend_score,
                regime=regime,
                reason=reason,
            )

        if horizon == "intraday":
            score = self._intraday_score(
                range_pct=range_pct,
                rvol=rvol,
                spread_pct=spread_pct,
                turnover=turnover,
                impulse_score=impulse_score,
                trend_score=trend_score,
            )
        elif horizon == "swing":
            score = self._swing_score(
                range_pct=range_pct,
                rvol=rvol,
                spread_pct=spread_pct,
                turnover=turnover,
                impulse_score=impulse_score,
                trend_score=trend_score,
            )
        else:
            score = 0.0
            reason = "unsupported_horizon"

        return VolatilityCandidate(
            symbol=symbol,
            horizon=horizon,
            score=round(float(score), 6),
            spread_pct=round(float(spread_pct), 6),
            range_pct=round(float(range_pct), 6),
            turnover=round(float(turnover), 2),
            rvol=round(float(rvol), 6),
            impulse_score=round(float(impulse_score), 6),
            trend_score=round(float(trend_score), 6),
            regime=regime,
            reason=reason or "passed",
        )

    def _passes_filters(
        self,
        *,
        horizon: str,
        symbol: str,
        turnover: float,
        spread_pct: float,
        range_pct: float,
        rvol: float,
    ) -> tuple[bool, str]:
        if not symbol:
            return False, "empty_symbol"
        if turnover < self.min_turnover:
            return False, f"turnover_too_low:{turnover:.0f}<{self.min_turnover:.0f}"
        if spread_pct > self.max_spread_pct:
            return False, f"spread_too_wide:{spread_pct:.6f}>{self.max_spread_pct:.6f}"

        if horizon == "intraday":
            if range_pct < self.min_range_pct_intraday:
                return False, f"range_too_low:{range_pct:.6f}<{self.min_range_pct_intraday:.6f}"
            if rvol < self.min_rvol_intraday:
                return False, f"rvol_too_low:{rvol:.6f}<{self.min_rvol_intraday:.6f}"
        elif horizon == "swing":
            if range_pct < self.min_range_pct_swing:
                return False, f"range_too_low:{range_pct:.6f}<{self.min_range_pct_swing:.6f}"
            if rvol < self.min_rvol_swing:
                return False, f"rvol_too_low:{rvol:.6f}<{self.min_rvol_swing:.6f}"
        else:
            return False, "unsupported_horizon"

        return True, "passed"

    def _intraday_score(
        self,
        *,
        range_pct: float,
        rvol: float,
        spread_pct: float,
        turnover: float,
        impulse_score: float,
        trend_score: float,
    ) -> float:
        liquidity_score = min(turnover / max(self.min_turnover, 1.0), 5.0)
        spread_score = max(0.0, 1.0 - spread_pct / max(self.max_spread_pct, 0.000001))
        return (
            range_pct * 35.0
            + min(rvol, 5.0) * 0.25
            + impulse_score * 1.2
            + abs(trend_score) * 0.8
            + liquidity_score * 0.15
            + spread_score * 0.2
        )

    def _swing_score(
        self,
        *,
        range_pct: float,
        rvol: float,
        spread_pct: float,
        turnover: float,
        impulse_score: float,
        trend_score: float,
    ) -> float:
        liquidity_score = min(turnover / max(self.min_turnover, 1.0), 5.0)
        spread_score = max(0.0, 1.0 - spread_pct / max(self.max_spread_pct, 0.000001))
        return (
            range_pct * 25.0
            + min(rvol, 4.0) * 0.15
            + impulse_score * 0.7
            + abs(trend_score) * 1.1
            + liquidity_score * 0.25
            + spread_score * 0.15
        )

    @staticmethod
    def _num(value: Any, default: float) -> float:
        try:
            if value is None or value == "":
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _spread_pct(*, bid: float, ask: float, last: float) -> float:
        if bid <= 0 or ask <= 0 or ask < bid:
            return 0.0
        base = last if last > 0 else mean([bid, ask])
        if base <= 0:
            return 0.0
        return (ask - bid) / base

    @staticmethod
    def _range_pct(*, high: float, low: float, base: float) -> float:
        if high <= 0 or low <= 0 or high < low or base <= 0:
            return 0.0
        return (high - low) / base

    @staticmethod
    def _rvol(*, volume: float, avg_volume: float) -> float:
        if avg_volume <= 0:
            return 1.0 if volume > 0 else 0.0
        return volume / avg_volume

    @staticmethod
    def _trend_score(*, open_price: float, close: float) -> float:
        if open_price <= 0 or close <= 0:
            return 0.0
        return (close - open_price) / open_price

    @staticmethod
    def _impulse_score(*, range_pct: float, rvol: float, trend_score: float) -> float:
        return abs(trend_score) * max(rvol, 0.0) + range_pct * min(max(rvol, 0.0), 5.0)

    @staticmethod
    def _regime(*, range_pct: float, rvol: float, trend_score: float) -> str:
        if range_pct >= 0.04 and rvol >= 1.5:
            return "expansion_up" if trend_score >= 0 else "expansion_down"
        if range_pct >= 0.02 and rvol >= 1.2:
            return "trend_up" if trend_score >= 0 else "trend_down"
        if range_pct < 0.01 and rvol < 0.8:
            return "compression"
        return "neutral"
