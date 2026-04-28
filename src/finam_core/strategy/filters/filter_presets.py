# -*- coding: utf-8 -*-
"""
filter_presets.py — пресеты фильтров по инструментам.

Русский коммент:
Здесь храним только конфигурацию фильтров.
Стратегия, риск и исполнение не зависят от конкретных инструментов.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


FILTER_PRESETS: dict[str, dict[str, Any]] = {
    "BRM6@RTSX": {
        "aggressive": {
            "tradeability_gate": "",
            "tradeability_min_range_atr": 1.5,
            "tradeability_max_range_atr": 0.0,
            "regime_ema_slope": "on",
            "regime_ema_slope_lookback": 10,
            "regime_ema_slope_threshold": 0.003,
            "regime_adaptive_mode": "slope_switch",
            "regime_trend_confirm_bars": 2,
        },
        "conservative": {
            "tradeability_gate": "range_atr_band",
            "tradeability_min_range_atr": 5.0,
            "tradeability_max_range_atr": 10.0,
            "regime_ema_slope": "on",
            "regime_ema_slope_lookback": 10,
            "regime_ema_slope_threshold": 0.003,
            "regime_adaptive_mode": "slope_switch",
            "regime_trend_confirm_bars": 2,
        },
    },
    "NGM6@RTSX": {
        "no_trade": {
            "mode": "NO_TRADE",
            "reason": "no stable edge on WF",
        },
    },
}


def get_filter_preset(symbol: str, profile: str) -> Dict[str, Any]:
    """Русский коммент: возвращает копию пресета, чтобы вызывающий код не менял глобальную конфигурацию."""
    symbol_presets = FILTER_PRESETS.get(symbol)
    if not symbol_presets:
        raise KeyError(f"No filter presets for symbol={symbol}")

    preset = symbol_presets.get(profile)
    if not preset:
        available = ",".join(sorted(symbol_presets.keys()))
        raise KeyError(f"No filter preset profile={profile} for symbol={symbol}; available={available}")

    return deepcopy(preset)
