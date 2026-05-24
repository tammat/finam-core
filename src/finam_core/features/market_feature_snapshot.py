from __future__ import annotations

from dataclasses import dataclass


def normalize_root_symbol(symbol: str) -> str:
    """Русский комментарий: нормализуем контракт/инструмент до базового root_symbol."""
    if symbol.startswith("NG") and symbol.endswith("@RTSX"):
        return "NG"
    if symbol.startswith("BR") and symbol.endswith("@RTSX"):
        return "BR"
    if symbol.startswith("USDRUB") and symbol.endswith("@RTSX"):
        return "USDRUB"
    if symbol.startswith("CNYRUB"):
        return "CNY"
    if (symbol.startswith("GD") or symbol.startswith("GL")) and symbol.endswith("@RTSX"):
        return "GOLD"
    if symbol.startswith("SV") and symbol.endswith("@RTSX"):
        return "SILVER"
    return symbol


@dataclass(frozen=True)
class MarketFeatureSnapshot:
    """Русский комментарий: расчетный контекст рынка на момент бара."""

    symbol: str
    root_symbol: str
    timeframe: str
    ts: str
    close: float
    return_1: float
    return_n: float
    atr_proxy: float
    volatility_state: str
    trend_state: str
    range_state: str
    session_state: str
    intermarket_risk_mode: str
    intermarket_commodity_mode: str
    fx_stress_score: float
    commodity_score: float
    quality: str
    reason: str


def classify_volatility(atr_proxy: float) -> str:
    """Русский комментарий: простая v1-классификация волатильности по ATR proxy."""
    atr = abs(float(atr_proxy))
    if atr <= 0:
        return "unknown"
    if atr < 0.0005:
        return "low"
    if atr < 0.0020:
        return "normal"
    return "high"


def classify_trend(return_n: float) -> str:
    """Русский комментарий: v1-тренд по накопленной доходности."""
    value = float(return_n)
    if value > 0.001:
        return "up"
    if value < -0.001:
        return "down"
    return "flat"


def classify_range(return_1: float, atr_proxy: float) -> str:
    """Русский комментарий: грубая оценка импульса/сжатия."""
    r1 = abs(float(return_1))
    atr = abs(float(atr_proxy))
    if atr <= 0:
        return "unknown"
    if r1 > atr * 1.5:
        return "impulse"
    if r1 < atr * 0.35:
        return "compression"
    return "normal"


def classify_session_state(ts_hour_utc: int) -> str:
    """Русский комментарий: приближенная сессионная классификация для MOEX по UTC."""
    if 4 <= ts_hour_utc < 8:
        return "MOEX_MORNING"
    if 8 <= ts_hour_utc < 16:
        return "MOEX_DAY"
    if 16 <= ts_hour_utc < 21:
        return "MOEX_EVENING"
    return "OFF_SESSION"


def calculate_snapshot_quality(
    *,
    intermarket_risk_mode: str,
    intermarket_commodity_mode: str,
    atr_proxy: float,
) -> tuple[str, str]:
    """Русский комментарий: качество snapshot зависит от полноты контекста."""
    missing: list[str] = []

    if intermarket_risk_mode == "unknown":
        missing.append("intermarket_risk_mode")
    if intermarket_commodity_mode == "unknown":
        missing.append("intermarket_commodity_mode")
    if atr_proxy == 0:
        missing.append("atr_proxy")

    if missing:
        return "PARTIAL", "missing:" + ",".join(missing)

    return "FULL", "feature_snapshot_complete"
