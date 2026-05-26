from __future__ import annotations

from typing import Any


_UNKNOWN = {"", "unknown", "UNKNOWN", "none", "None", "null", None}


def is_known_regime(value: Any) -> bool:
    return value not in _UNKNOWN


def _first_known(*values: Any) -> Any:
    """Русский комментарий: возвращает первое заполненное значение, не теряя 0."""
    for value in values:
        if value not in _UNKNOWN:
            return value
    return None


def derive_regime_label(payload: dict[str, Any] | None) -> str:
    """Русский комментарий: единый derivation regime label для analytics/outcomes."""

    if not isinstance(payload, dict):
        return "unknown"

    for key in ("regime", "regime_label", "regime_direction_label"):
        value = payload.get(key)
        if is_known_regime(value):
            return str(value).lower()

    # Русский комментарий: fallback для BR strategy, когда regime не передан численно,
    # но направление/волатильность зашиты в reason сигнала.
    reason = str(
        payload.get("reason")
        or payload.get("signal_reason")
        or payload.get("strategy_reason")
        or ""
    ).lower()

    if reason:
        if "breakout_up" in reason or "_up_" in reason:
            trend = "trend_up"
        elif "breakout_down" in reason or "_down_" in reason:
            trend = "trend_down"
        else:
            trend = ""

        if "high_vol" in reason or "trend_high_vol" in reason:
            vol = "high_vol"
        elif "low_vol" in reason:
            vol = "low_vol"
        elif trend:
            vol = "normal_vol"
        else:
            vol = ""

        if trend and vol:
            return f"{trend}_{vol}"

    market = payload.get("market") if isinstance(payload.get("market"), dict) else {}
    snapshot = payload.get("trade_context_snapshot") if isinstance(payload.get("trade_context_snapshot"), dict) else {}
    snapshot_market = snapshot.get("market") if isinstance(snapshot.get("market"), dict) else {}

    direction = _first_known(
        payload.get("regime_direction"),
        market.get("regime_direction"),
        snapshot_market.get("regime_direction"),
    )

    atr_pct = _first_known(
        payload.get("regime_atr_pct"),
        market.get("regime_atr_pct"),
        snapshot_market.get("regime_atr_pct"),
    )

    try:
        direction_f = float(direction)
    except Exception:
        return "unknown"

    try:
        atr_f = float(atr_pct) if atr_pct is not None else 0.0
    except Exception:
        atr_f = 0.0

    if direction_f > 0:
        trend = "trend_up"
    elif direction_f < 0:
        trend = "trend_down"
    else:
        trend = "flat"

    vol = "high_vol" if atr_f >= 0.003 else "normal_vol"

    return f"{trend}_{vol}"
