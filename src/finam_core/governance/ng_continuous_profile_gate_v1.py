from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgContinuousProfileDecisionV1:
    symbol: str
    side: str
    hour_msk: int
    allowed: bool
    profile_trades: int
    profile_expectancy: float | None
    reason: str


class NgContinuousProfileGateV1:
    """
    Русский комментарий:
    Paper-only gate для NG BUY pilot.
    Профиль: NG_CONTINUOUS + side + hour_msk.
    """

    def __init__(
        self,
        *,
        min_profile_trades: int = 20,
        min_expectancy: float = 0.0,
    ) -> None:
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
    ) -> NgContinuousProfileDecisionV1:
        side_norm = str(side or "").upper()

        if side_norm != "BUY":
            return NgContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
                reason="ng_paper_pilot_buy_only",
            )

        if profile_expectancy is None:
            return NgContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=None,
                reason="ng_profile_no_expectancy",
            )

        if profile_trades < self.min_profile_trades:
            return NgContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
                reason="ng_profile_insufficient_trades",
            )

        if float(profile_expectancy) <= self.min_expectancy:
            return NgContinuousProfileDecisionV1(
                symbol=symbol,
                side=side_norm,
                hour_msk=hour_msk,
                allowed=False,
                profile_trades=profile_trades,
                profile_expectancy=profile_expectancy,
                reason="ng_profile_non_positive_expectancy",
            )

        return NgContinuousProfileDecisionV1(
            symbol=symbol,
            side=side_norm,
            hour_msk=hour_msk,
            allowed=True,
            profile_trades=profile_trades,
            profile_expectancy=profile_expectancy,
            reason="ng_paper_pilot_allowed",
        )
