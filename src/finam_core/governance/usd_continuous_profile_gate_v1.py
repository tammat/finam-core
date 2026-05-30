from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UsdContinuousProfileDecisionV1:
    symbol: str
    side: str
    hour_msk: int
    allowed: bool
    profile_trades: int
    profile_expectancy: float | None
    reason: str


class UsdContinuousProfileGateV1:
    """
    Русский комментарий:
    Paper-only gate для USD BUY pilot.
    Профиль: USD_CONTINUOUS + side + hour_msk.
    """

    def __init__(self, *, min_profile_trades: int = 20, min_expectancy: float = 0.0) -> None:
        self.min_profile_trades = int(min_profile_trades)
        self.min_expectancy = float(min_expectancy)

    def decide(
        self,
        *,
        symbol: str,
        side: str,
        hour_msk: int,
        profile_trades: int,
        profile_expectancy: float | None,
    ) -> UsdContinuousProfileDecisionV1:
        side_norm = str(side or "").upper()

        if side_norm != "BUY":
            return UsdContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
                reason="usd_paper_pilot_buy_only",
            )

        if profile_expectancy is None:
            return UsdContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=None,
                reason="usd_profile_no_expectancy",
            )

        if profile_trades < self.min_profile_trades:
            return UsdContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
                reason="usd_profile_insufficient_trades",
            )

        if float(profile_expectancy) <= self.min_expectancy:
            return UsdContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
                reason="usd_profile_non_positive_expectancy",
            )

        return UsdContinuousProfileDecisionV1(
            symbol=symbol,
            side=side_norm,
            hour_msk=hour_msk,
            allowed=True,
            profile_trades=profile_trades,
            profile_expectancy=profile_expectancy,
            reason="usd_paper_pilot_allowed",
        )
