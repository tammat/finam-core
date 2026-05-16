from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OpportunityCandidate:
    symbol: str
    atr_pct: float
    rvol: float
    turnover: float
    spread_pct: float
    regime: str
    smart_money_score: float = 0.0
    smart_money_label: str = "NO_SMART_MONEY_DATA"
    opportunity_score: float = 0.0
    strategy: str = ""


class MOEXOpportunityScanner:
    """
    Русский комментарий:
    Сканер ищет лучшие intraday opportunities
    среди ликвидных волатильных акций.
    """

    def __init__(
        self,
        min_turnover: float = 50_000_000,
        max_spread_pct: float = 0.003,
        min_atr_pct: float = 0.008,
        min_rvol: float = 1.2,
    ) -> None:
        self.min_turnover = min_turnover
        self.max_spread_pct = max_spread_pct
        self.min_atr_pct = min_atr_pct
        self.min_rvol = min_rvol

    def evaluate(
        self,
        symbol: str,
        atr_pct: float,
        rvol: float,
        turnover: float,
        spread_pct: float,
        regime: str,
        smart_money_score: float = 0.0,
        smart_money_label: str = "NO_SMART_MONEY_DATA",
    ) -> OpportunityCandidate | None:

        if turnover < self.min_turnover:
            return None

        if spread_pct > self.max_spread_pct:
            return None

        if atr_pct < self.min_atr_pct:
            return None

        if rvol < self.min_rvol:
            return None

        # Русский комментарий:
        # Нормализуем компоненты score, чтобы огромный turnover
        # не "взрывал" итоговую оценку opportunity.
        turnover_score = min(turnover / 1_000_000_000, 1.0)
        rvol_score = min(rvol / 5.0, 1.0)
        atr_score = min(atr_pct / 0.05, 1.0)
        spread_penalty = min(spread_pct / 0.01, 1.0)

        smart_money_score = max(0.0, min(float(smart_money_score or 0.0), 1.0))

        score = (
            atr_score * 0.30
            + rvol_score * 0.25
            + turnover_score * 0.15
            + smart_money_score * 0.20
            - spread_penalty * 0.10
        )

        strategy = self.select_strategy(
            regime=regime,
            atr_pct=atr_pct,
            rvol=rvol,
        )

        return OpportunityCandidate(
            symbol=symbol,
            atr_pct=round(atr_pct, 6),
            rvol=round(rvol, 4),
            turnover=round(turnover, 2),
            spread_pct=round(spread_pct, 6),
            regime=regime,
            smart_money_score=round(smart_money_score, 6),
            smart_money_label=str(smart_money_label or "NO_SMART_MONEY_DATA"),
            opportunity_score=round(score, 6),
            strategy=strategy,
        )

    @staticmethod
    def select_strategy(
        regime: str,
        atr_pct: float,
        rvol: float,
    ) -> str:

        regime = (regime or "").lower()

        if "trend" in regime and atr_pct >= 0.01 and rvol >= 1.5:
            return "VOLATILITY_BREAKOUT_EQUITY"

        if "trend" in regime:
            return "TREND_PULLBACK_EQUITY"

        return "NO_TRADE"

    def rank(
        self,
        candidates: list[OpportunityCandidate],
    ) -> list[OpportunityCandidate]:

        return sorted(
            candidates,
            key=lambda x: x.opportunity_score,
            reverse=True,
        )
