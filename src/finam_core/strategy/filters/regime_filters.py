# -*- coding: utf-8 -*-
"""
regime_filters.py — общий слой regime/tradeability-фильтров.

Русский коммент:
Модуль не знает о стратегии, заявках, исполнении и портфеле.
Он только считает признаки режима и отвечает: разрешён ли вход.
"""

import math
from typing import Optional

import pandas as pd


def compute_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Русский коммент: классический True Range для ATR/режимных фильтров."""
    prev_close = close.shift(1)
    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def compute_range_atr(
    high: pd.Series,
    low: pd.Series,
    true_range: pd.Series,
    atr_n: int,
    range_window: int,
) -> pd.Series:
    """Русский коммент: отношение диапазона рынка к ATR — простая оценка торгуемости."""
    atr = true_range.rolling(int(atr_n)).mean()
    price_range = high.rolling(int(range_window)).max() - low.rolling(int(range_window)).min()
    return price_range / atr.replace(0, math.nan)


def ema_slope_value_at(
    ema: Optional[pd.Series],
    i: int,
    lookback: int,
) -> float:
    """Русский коммент: нормированный наклон EMA на заданном lookback."""
    if ema is None:
        return 0.0
    lookback = int(lookback)
    if i < lookback:
        return 0.0

    ema_now = ema.iat[i]
    ema_prev = ema.iat[i - lookback]

    if pd.isna(ema_now) or pd.isna(ema_prev) or ema_prev == 0:
        return 0.0

    return float((ema_now - ema_prev) / ema_prev)


def range_atr_allows(
    range_atr: pd.Series,
    i: int,
    min_range_atr: float,
) -> bool:
    """Русский коммент: gate входов — рынок должен иметь достаточный ход относительно шума."""
    value = range_atr.iat[i]
    if pd.isna(value):
        return False
    return float(value) >= float(min_range_atr)


from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class FilterDecision:
    """Русский коммент: единое решение фильтров для backtest и live pipeline."""
    allowed: bool
    reason: str = "allowed"
    details: Dict[str, Any] | None = None


@dataclass(frozen=True)
class FilterContext:
    """Русский коммент: контекст фильтрации для единого API backtest/live."""
    range_atr: Optional[pd.Series] = None
    ema: Optional[pd.Series] = None
    session_allowed: bool = True
    regime_allowed: bool = True
    mr_allowed: bool = True


class FilterEngine:
    """Русский коммент: единый слой regime/tradeability-фильтров без зависимости от execution/risk."""

    def __init__(self, params: Dict[str, Any] | None = None):
        self.params = params or {}

    def allow(self, i: int, context: FilterContext) -> FilterDecision:
        """Русский коммент: единая точка фильтрации сигнала для backtest и live pipeline."""
        if not context.session_allowed:
            return FilterDecision(False, "session_fail")
        if not context.mr_allowed:
            return FilterDecision(False, "mr_regime_fail")
        if not context.regime_allowed:
            return FilterDecision(False, "regime_fail")

        ema_decision = self.evaluate_ema_slope(context.ema, i)
        if not ema_decision.allowed:
            return ema_decision

        gate = self._as_str(self.params.get("tradeability_gate"), "")
        if gate not in ("", "off", "none"):
            if context.range_atr is None:
                return FilterDecision(False, "tradeability_missing_range_atr")
            tradeability_decision = self.evaluate_range_atr(context.range_atr, i)
            if not tradeability_decision.allowed:
                return tradeability_decision

        return FilterDecision(True, "allowed")

    @staticmethod
    def _as_str(value: Any, default: str = "") -> str:
        return str(value if value is not None else default).strip().lower()

    @staticmethod
    def _as_int(value: Any, default: int) -> int:
        try:
            return int(value if value is not None else default)
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _as_float(value: Any, default: float) -> float:
        try:
            return float(value if value is not None else default)
        except (TypeError, ValueError):
            return float(default)

    def evaluate_range_atr(self, range_atr: pd.Series, i: int) -> FilterDecision:
        gate = self._as_str(self.params.get("tradeability_gate"), "")
        if gate in ("", "off", "none"):
            return FilterDecision(True, "tradeability_off")
        if gate != "range_atr":
            return FilterDecision(True, "tradeability_unknown_gate")

        min_range_atr = self._as_float(self.params.get("tradeability_min_range_atr"), 1.5)
        value = range_atr.iat[i]
        if pd.isna(value):
            return FilterDecision(False, "tradeability_nan", {"min_range_atr": min_range_atr})

        allowed = float(value) >= min_range_atr
        return FilterDecision(
            allowed,
            "allowed" if allowed else "tradeability_range_atr_fail",
            {"range_atr": float(value), "min_range_atr": min_range_atr},
        )

    def evaluate_ema_slope(self, ema: pd.Series | None, i: int) -> FilterDecision:
        regime_ema_slope = self._as_str(self.params.get("regime_ema_slope"), "")
        if regime_ema_slope != "on":
            return FilterDecision(True, "ema_slope_off")

        adaptive_mode = self._as_str(self.params.get("regime_adaptive_mode"), "")
        if adaptive_mode == "slope_switch":
            return FilterDecision(True, "ema_slope_adaptive_mode")

        lookback = self._as_int(self.params.get("regime_ema_slope_lookback"), 20)
        threshold = self._as_float(self.params.get("regime_ema_slope_threshold"), 0.002)
        slope = ema_slope_value_at(ema, i, lookback)
        allowed = abs(slope) <= threshold

        return FilterDecision(
            allowed,
            "allowed" if allowed else "ema_slope_fail",
            {"slope": slope, "threshold": threshold, "lookback": lookback},
        )
