# Русский комментарий: Regime Layer для Brent/BR.
# Фильтр не отправляет заявки, только классифицирует режим и разрешает/блокирует сигнал.

from __future__ import annotations

from dataclasses import dataclass

from finam_core.strategy.br_volatility_intelligence import (
    BRVolatilityIntelligence,
    BRVolatilityProfile,
)


@dataclass(frozen=True)
class BRRegimeDecision:
    allowed: bool
    regime: str
    reason: str
    size_multiplier: float
    confirmation_required: bool = False
    confirmation_ticks: int = 3
    breakout_k: float = 1.0


class BRRegimeLayer:
    def __init__(self) -> None:
        self.volatility = BRVolatilityIntelligence()

    def evaluate(
        self,
        *,
        atr_pct: float,
        slope_m5: float,
        slope_m15: float,
        compression_ratio: float,
        signal_side: str,
        price: float = 0.0,
        atr_short: float = 0.0,
        atr_long: float = 0.0,
        volatility_profile: BRVolatilityProfile | None = None,
    ) -> BRRegimeDecision:
        side = str(signal_side or "").upper()

        if volatility_profile is None and price > 0 and atr_short > 0 and atr_long > 0:
            volatility_profile = self.volatility.evaluate(
                atr_short=atr_short,
                atr_long=atr_long,
                price=price,
            )

        vol_regime = getattr(volatility_profile, "volatility_regime", "manual")
        vol_size_multiplier = float(getattr(volatility_profile, "size_multiplier", 1.0) or 0.0)
        vol_confirmation_ticks = int(getattr(volatility_profile, "confirmation_ticks", 3) or 3)
        vol_breakout_k = float(getattr(volatility_profile, "breakout_k", 1.0) or 1.0)

        if atr_pct <= 0:
            return BRRegimeDecision(
                False,
                "unknown",
                "invalid_atr",
                0.0,
                confirmation_required=False,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        if vol_regime == "panic_vol":
            return BRRegimeDecision(
                False,
                "panic_vol",
                "volatility_too_high",
                0.0,
                confirmation_required=False,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        if atr_pct < 0.0015:
            return BRRegimeDecision(
                False,
                "dead_market",
                "volatility_too_low",
                0.0,
                confirmation_required=False,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        if atr_pct > 0.035:
            return BRRegimeDecision(
                False,
                "panic",
                "volatility_too_high",
                0.0,
                confirmation_required=False,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        if compression_ratio < 0.65:
            return BRRegimeDecision(
                True,
                "compression",
                "confirmation_required",
                vol_size_multiplier if vol_size_multiplier > 0 else 0.5,
                confirmation_required=True,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        trend_up = slope_m5 > 0 and slope_m15 > 0
        trend_down = slope_m5 < 0 and slope_m15 < 0

        if side == "BUY" and trend_up:
            return BRRegimeDecision(
                True,
                "trend_expansion_up" if vol_regime != "expansion" else "volatility_expansion_up",
                "trend_confirmed",
                vol_size_multiplier if vol_size_multiplier > 0 else 1.0,
                confirmation_required=False,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        if side == "SELL" and trend_down:
            return BRRegimeDecision(
                True,
                "trend_expansion_down" if vol_regime != "expansion" else "volatility_expansion_down",
                "trend_confirmed",
                vol_size_multiplier if vol_size_multiplier > 0 else 1.0,
                confirmation_required=False,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        if abs(slope_m5) < 0.0002 and abs(slope_m15) < 0.0002:
            return BRRegimeDecision(
                False,
                "range",
                "flat_chop_block",
                0.0,
                confirmation_required=False,
                confirmation_ticks=vol_confirmation_ticks,
                breakout_k=vol_breakout_k,
            )

        return BRRegimeDecision(
            False,
            "misaligned",
            "signal_not_aligned_with_regime",
            0.0,
            confirmation_required=False,
            confirmation_ticks=vol_confirmation_ticks,
            breakout_k=vol_breakout_k,
        )
