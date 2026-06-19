# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentSignalProfile:
    """Русский комментарий: профиль сигнальных порогов по классу инструмента.

    Это не execution-конфиг. Профиль используется только для research/watch слоя.
    """
    asset_class: str
    timeframe: str
    atr_min_pct: float
    volume_mult: float | None
    breakout_lookback: int
    use_volume_filter: bool
    notes: str


def resolve_instrument_signal_profile(symbol: str, timeframe: str = "M5") -> InstrumentSignalProfile:

    upper_symbol = str(symbol).strip().upper()

    if upper_symbol.startswith("USDRUBF") or upper_symbol.startswith("CNYRUBF"):
        return InstrumentSignalProfile(
            asset_class="FX_FUTURES",
            timeframe=timeframe,
            atr_min_pct=0.0005,
            volume_mult=1.0,
            use_volume_filter=True,
            breakout_lookback=30,
            notes="fx_watchlist_v1: watch-only FX futures profile",
        )

    if upper_symbol.startswith("CNYRUB_TOM"):
        return InstrumentSignalProfile(
            asset_class="FX_SPOT",
            timeframe=timeframe,
            atr_min_pct=0.0004,
            volume_mult=1.0,
            use_volume_filter=True,
            breakout_lookback=30,
            notes="fx_watchlist_v1: watch-only FX spot/TOM profile",
        )

    symbol_upper = str(symbol).upper()
    timeframe_upper = str(timeframe).upper()

    if symbol_upper.endswith("@MISX") and not symbol_upper.startswith("IMOEX"):
        return InstrumentSignalProfile(
            asset_class="EQUITY",
            timeframe=timeframe_upper,
            atr_min_pct=0.0005,
            volume_mult=1.0,
            breakout_lookback=30,
            use_volume_filter=True,
            notes="Акции MOEX: ATR и volume должны быть мягче, чем у futures.",
        )

    if symbol_upper.startswith("BR") or "BR@" in symbol_upper:
        return InstrumentSignalProfile(
            asset_class="BRENT_FUTURES",
            timeframe=timeframe_upper,
            atr_min_pct=0.0015,
            volume_mult=1.2,
            breakout_lookback=30,
            use_volume_filter=True,
            notes="Brent futures: отдельный профиль, не наследовать equity thresholds.",
        )

    if symbol_upper.startswith("NG") or "NG@" in symbol_upper:
        return InstrumentSignalProfile(
            asset_class="GAS_FUTURES",
            timeframe=timeframe_upper,
            atr_min_pct=0.0020,
            volume_mult=1.2,
            breakout_lookback=30,
            use_volume_filter=True,
            notes="Natural Gas futures: выше шум и гэпы, нужен отдельный ATR profile.",
        )

    if symbol_upper.startswith("GD") or "GD@" in symbol_upper:
        return InstrumentSignalProfile(
            asset_class="GOLD_FUTURES",
            timeframe=timeframe_upper,
            atr_min_pct=0.0010,
            volume_mult=1.2,
            breakout_lookback=30,
            use_volume_filter=True,
            notes="Gold futures: отдельный профиль, ниже шум, чем NG, но не equity thresholds.",
        )

    if "IMOEX" in symbol_upper or symbol_upper.startswith("MX") or symbol_upper.startswith("MOEX"):
        return InstrumentSignalProfile(
            asset_class="MOEX_INDEX",
            timeframe=timeframe_upper,
            atr_min_pct=0.0007,
            volume_mult=None,
            breakout_lookback=30,
            use_volume_filter=False,
            notes="Индекс: volume filter обычно неприменим напрямую; использовать price/regime filter.",
        )

    return InstrumentSignalProfile(
        asset_class="UNKNOWN",
        timeframe=timeframe_upper,
        atr_min_pct=0.0010,
        volume_mult=None,
        breakout_lookback=30,
        use_volume_filter=False,
        notes="Неизвестный инструмент: только research/watch, без runtime promotion.",
    )
