from __future__ import annotations

from typing import Any


class RegimeLabeler:
    """
    Русский комментарий:
    Единый классификатор рыночного режима для attribution.

    Назначение:
    - убрать UNKNOWN из fills/trades;
    - дать analytics стабильный regime label.
    """

    @staticmethod
    def label(state: dict[str, Any] | None = None, features: dict[str, Any] | None = None) -> str:
        state = state or {}
        features = features or {}

        trend = str(
            state.get("regime_trend")
            or state.get("trend")
            or features.get("trend")
            or ""
        ).lower()

        volatility = str(
            state.get("regime_vol")
            or state.get("volatility")
            or features.get("volatility")
            or ""
        ).lower()

        atr_pct = RegimeLabeler._float_or_none(
            state.get("atr_pct")
            or features.get("atr_pct")
        )

        compression = bool(
            state.get("compression")
            or features.get("compression")
            or False
        )

        breakout = bool(
            state.get("breakout")
            or features.get("breakout")
            or False
        )

        if breakout:
            return "breakout"

        if compression:
            return "compression"

        trend_label = RegimeLabeler._trend_label(trend)
        vol_label = RegimeLabeler._vol_label(volatility, atr_pct)

        return f"{trend_label}_{vol_label}"

    @staticmethod
    def _trend_label(value: str) -> str:
        value = value.lower()

        if value in ("up", "bull", "bullish", "trend_up", "long", "buy"):
            return "trend_up"

        if value in ("down", "bear", "bearish", "trend_down", "short", "sell"):
            return "trend_down"

        if "trend" in value:
            return "trend"

        if value in ("range", "flat", "sideways", "neutral"):
            return "range"

        return "unknown_trend"

    @staticmethod
    def _vol_label(value: str, atr_pct: float | None = None) -> str:
        value = value.lower()

        if value in ("high", "high_vol", "volatile"):
            return "high_vol"

        if value in ("low", "low_vol", "quiet"):
            return "low_vol"

        if value in ("normal", "normal_vol", "medium", "medium_vol"):
            return "normal_vol"

        if atr_pct is not None:
            if atr_pct >= 0.015:
                return "high_vol"
            if atr_pct <= 0.005:
                return "low_vol"
            return "normal_vol"

        return "unknown_vol"

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None
