from __future__ import annotations

from dataclasses import dataclass


def normalize_root_symbol(symbol: str) -> str:
    """Русский комментарий: нормализуем фьючерсный контракт до базового инструмента."""
    if symbol.startswith("NG") and symbol.endswith("@RTSX"):
        return "NG"
    if symbol.startswith("BR") and symbol.endswith("@RTSX"):
        return "BR"
    if symbol.startswith("USDRUB") and symbol.endswith("@RTSX"):
        return "USDRUB"
    return symbol


@dataclass(frozen=True)
class ClosedTradeQuality:
    """Русский комментарий: расчетные показатели качества закрытой сделки."""

    mae: float
    mfe: float
    realized_rr: float
    quality_score: float


def calculate_closed_trade_quality(
    *,
    side: str,
    entry_price: float,
    exit_price: float,
    stop_distance: float | None = None,
) -> ClosedTradeQuality:
    """
    Русский комментарий:
    v2-базовая оценка без прохода по барам.

    Ограничение:
    - MAE/MFE пока считаются приближенно по entry/exit;
    - точный MAE/MFE по барам добавим в v2.1.
    """
    side_u = side.upper()

    if side_u == "LONG":
        pnl_per_unit = exit_price - entry_price
    else:
        pnl_per_unit = entry_price - exit_price

    if pnl_per_unit >= 0:
        mfe = abs(pnl_per_unit)
        mae = 0.0
    else:
        mfe = 0.0
        mae = -abs(pnl_per_unit)

    initial_risk = abs(stop_distance) if stop_distance and abs(stop_distance) > 0 else max(abs(pnl_per_unit), 0.000001)
    realized_rr = pnl_per_unit / initial_risk

    # Русский комментарий: мягкая шкала качества, чтобы не раздувать score на микросделках.
    quality_score = max(-1.0, min(1.0, realized_rr / 3.0))

    return ClosedTradeQuality(
        mae=round(mae, 8),
        mfe=round(mfe, 8),
        realized_rr=round(realized_rr, 8),
        quality_score=round(quality_score, 8),
    )
