from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrShortShadowDecisionV1:
    allowed: bool
    shadow_logged: bool
    reason: str


class BrShortShadowPolicyV1:
    """
    Русский комментарий:
    Shadow-policy для BR short.
    Ничего не исполняет. Только классифицирует, был бы SELL при flat/short
    допустимым OPEN_SHORT-кандидатом.
    """

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        strategy: str,
        current_position: float,
    ) -> BrShortShadowDecisionV1:
        symbol_u = str(symbol or "").upper()
        side_u = str(side or "").upper()
        strategy_u = str(strategy or "")

        if not symbol_u.startswith("BR"):
            return BrShortShadowDecisionV1(True, False, "not_br")

        if side_u != "SELL":
            return BrShortShadowDecisionV1(True, False, "not_sell")

        if strategy_u != "BR_CONSERVATIVE_BREAKOUT":
            return BrShortShadowDecisionV1(
                False,
                True,
                "br_short_shadow_block_non_canonical_strategy",
            )

        if float(current_position or 0.0) > 0:
            return BrShortShadowDecisionV1(
                True,
                False,
                "br_sell_reduces_existing_long",
            )

        return BrShortShadowDecisionV1(
            True,
            True,
            "br_short_shadow_open_short_candidate",
        )
