# Русский комментарий: Regime Layer для Brent/BR.
# Фильтр не отправляет заявки, только классифицирует режим и разрешает/блокирует сигнал.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BRRegimeDecision:
    allowed: bool
    regime: str
    reason: str
    size_multiplier: float
    confirmation_required: bool = False


class BRRegimeLayer:
    def evaluate(
        self,
        *,
        atr_pct: float,
        slope_m5: float,
        slope_m15: float,
        compression_ratio: float,
        signal_side: str,
    ) -> BRRegimeDecision:
        side = str(signal_side or "").upper()

        if atr_pct <= 0:
            return BRRegimeDecision(False, "unknown", "invalid_atr", 0.0, confirmation_required=False)

        if atr_pct < 0.0015:
            return BRRegimeDecision(False, "dead_market", "volatility_too_low", 0.0, confirmation_required=False)

        if atr_pct > 0.035:
            return BRRegimeDecision(False, "panic", "volatility_too_high", 0.0, confirmation_required=False)

        if compression_ratio < 0.65:
            return BRRegimeDecision(True, "compression", "confirmation_required", 0.5, confirmation_required=True)

        trend_up = slope_m5 > 0 and slope_m15 > 0
        trend_down = slope_m5 < 0 and slope_m15 < 0

        if side == "BUY" and trend_up:
            return BRRegimeDecision(True, "trend_expansion_up", "trend_confirmed", 1.0, confirmation_required=False)

        if side == "SELL" and trend_down:
            return BRRegimeDecision(True, "trend_expansion_down", "trend_confirmed", 1.0, confirmation_required=False)

        if abs(slope_m5) < 0.0002 and abs(slope_m15) < 0.0002:
            return BRRegimeDecision(False, "range", "flat_chop_block", 0.0, confirmation_required=False)

        return BRRegimeDecision(False, "misaligned", "signal_not_aligned_with_regime", 0.0, confirmation_required=False)
