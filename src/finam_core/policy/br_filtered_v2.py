from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrFilteredV2Context:
    symbol: str
    timeframe: str
    side: str
    regime: str
    volatility_regime: str
    session_type: str
    confidence: float = 0.0


@dataclass(frozen=True)
class BrFilteredV2Decision:
    allowed: bool
    reason: str
    size_multiplier: float = 0.0


class BrFilteredV2Policy:
    """
    Русский комментарий:
    BR_FILTERED_V2 — усиление V1:
    - только SELL;
    - только подтвержденные regime/session профили;
    - минимальный confidence;
    - multiplier для последующего risk sizing.
    """

    min_confidence = 0.65

    profile_multipliers = {
        ("trend_up_expansion", "high", "main_2"): 1.00,
        ("trend_up_expansion", "high", "evening"): 0.85,
        ("trend_up_expansion", "high", "main_1"): 0.80,
        ("range_normal", "normal", "morning"): 0.75,
        ("trend_up", "normal", "main_1"): 0.75,
        ("trend_up", "normal", "evening"): 0.65,
    }

    def evaluate(self, ctx: BrFilteredV2Context) -> BrFilteredV2Decision:
        if not ctx.symbol.startswith("BR"):
            return BrFilteredV2Decision(True, "not_brent", 1.0)

        if ctx.timeframe != "M5":
            return BrFilteredV2Decision(False, "br_filtered_v2_blocks_non_m5", 0.0)

        if ctx.side != "SELL":
            return BrFilteredV2Decision(False, "br_filtered_v2_buy_disabled", 0.0)

        if ctx.regime.startswith("trend_down"):
            return BrFilteredV2Decision(False, "br_filtered_v2_blocks_trend_down", 0.0)

        if ctx.volatility_regime == "low":
            return BrFilteredV2Decision(False, "br_filtered_v2_blocks_low_vol", 0.0)

        if ctx.confidence < self.min_confidence:
            return BrFilteredV2Decision(False, "br_filtered_v2_low_confidence", 0.0)

        profile = (ctx.regime, ctx.volatility_regime, ctx.session_type)
        multiplier = self.profile_multipliers.get(profile)

        if multiplier is None:
            return BrFilteredV2Decision(False, "br_filtered_v2_profile_not_allowed", 0.0)

        return BrFilteredV2Decision(True, "br_filtered_v2_allowed", multiplier)
