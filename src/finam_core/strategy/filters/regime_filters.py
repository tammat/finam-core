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
