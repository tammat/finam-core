# Русский комментарий: Volatility-aware execution intelligence для Brent/BR.
# Модуль не отправляет заявки. Только рассчитывает режим волатильности и параметры допуска.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BRVolatilityProfile:
    volatility_regime: str
    atr_pct: float
    compression_ratio: float
    breakout_k: float
    size_multiplier: float
    confirmation_ticks: int
    reason: str


class BRVolatilityIntelligence:
    def evaluate(
        self,
        *,
        atr_short: float,
        atr_long: float,
        price: float,
    ) -> BRVolatilityProfile:
        if price <= 0 or atr_short <= 0 or atr_long <= 0:
            return BRVolatilityProfile(
                volatility_regime="unknown",
                atr_pct=0.0,
                compression_ratio=1.0,
                breakout_k=1.0,
                size_multiplier=0.0,
                confirmation_ticks=3,
                reason="invalid_input",
            )

        atr_pct = atr_short / price
        compression_ratio = atr_short / atr_long

        if atr_pct < 0.0015:
            return BRVolatilityProfile("dead_market", atr_pct, compression_ratio, 1.2, 0.0, 4, "vol_too_low")

        if atr_pct > 0.035:
            return BRVolatilityProfile("panic_vol", atr_pct, compression_ratio, 1.8, 0.25, 5, "vol_too_high")

        if compression_ratio < 0.65:
            return BRVolatilityProfile("compression", atr_pct, compression_ratio, 0.8, 0.5, 3, "compression_detected")

        if compression_ratio > 1.35:
            return BRVolatilityProfile("expansion", atr_pct, compression_ratio, 1.2, 1.0, 2, "expansion_detected")

        return BRVolatilityProfile("normal", atr_pct, compression_ratio, 1.0, 1.0, 3, "normal_vol")
