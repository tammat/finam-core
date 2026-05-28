from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrRegimeContext:
    symbol: str
    timeframe: str
    side: str
    regime: str
    volatility_regime: str
    session_type: str


class BrFilteredV1Policy:
    """
    Русский комментарий:
    Regime/session gate для Brent M5.
    Основан на rolling replay 2025-05-28 .. 2026-05-27.
    Разрешает только статистически подтвержденные SELL-сетапы.
    """

    allowed_sell_profiles = {
        ("trend_up", "normal", "main_1"),
        ("trend_up_expansion", "high", "main_2"),
        ("trend_up", "normal", "evening"),
        ("range_normal", "normal", "morning"),
        ("trend_up_expansion", "high", "evening"),
        ("trend_up_expansion", "high", "main_1"),
    }

    def allow(self, ctx: BrRegimeContext) -> tuple[bool, str]:
        if not ctx.symbol.startswith("BR"):
            return True, "not_brent"

        if ctx.timeframe != "M5":
            return False, "br_filtered_v1_blocks_non_m5"

        if ctx.side != "SELL":
            return False, "br_filtered_v1_buy_disabled"

        profile = (ctx.regime, ctx.volatility_regime, ctx.session_type)

        if profile in self.allowed_sell_profiles:
            return True, "br_filtered_v1_allowed_sell_profile"

        if ctx.regime.startswith("trend_down"):
            return False, "br_filtered_v1_blocks_trend_down_sell"

        if ctx.volatility_regime == "low":
            return False, "br_filtered_v1_blocks_low_vol"

        return False, "br_filtered_v1_profile_not_allowed"
