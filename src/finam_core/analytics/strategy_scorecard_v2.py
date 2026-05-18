from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyScorecard:
    strategy: str
    trades: int
    net_pnl: float
    expectancy: float
    winrate: float
    p_positive: float
    max_drawdown: float
    stability_score: float
    grade: str
    decision: str


class StrategyScorecardV2:
    """Русский комментарий: интегральная оценка устойчивости стратегии."""

    def build(
        self,
        *,
        strategy: str,
        trades: int,
        net_pnl: float,
        expectancy: float,
        winrate: float,
        p_positive: float,
        max_drawdown: float,
    ) -> StrategyScorecard:

        stability_score = self._calc_stability(
            expectancy=expectancy,
            p_positive=p_positive,
            winrate=winrate,
            max_drawdown=max_drawdown,
        )

        grade = self._grade(
            trades=trades,
            stability_score=stability_score,
            p_positive=p_positive,
            max_drawdown=max_drawdown,
        )

        decision = self._decision(grade)

        return StrategyScorecard(
            strategy=strategy,
            trades=trades,
            net_pnl=net_pnl,
            expectancy=expectancy,
            winrate=winrate,
            p_positive=p_positive,
            max_drawdown=max_drawdown,
            stability_score=stability_score,
            grade=grade,
            decision=decision,
        )

    def _calc_stability(
        self,
        *,
        expectancy: float,
        p_positive: float,
        winrate: float,
        max_drawdown: float,
    ) -> float:

        score = 0.0

        score += expectancy * 100.0
        score += p_positive * 40.0
        score += winrate * 20.0

        score -= abs(max_drawdown) * 10.0

        return round(score, 4)

    def _grade(
        self,
        *,
        trades: int,
        stability_score: float,
        p_positive: float,
        max_drawdown: float,
    ) -> str:

        if trades < 30:
            return "N"

        if p_positive >= 0.97 and stability_score >= 55:
            return "A+"

        if p_positive >= 0.92 and stability_score >= 45:
            return "A"

        if p_positive >= 0.85 and stability_score >= 30:
            return "B"

        if p_positive >= 0.70 and stability_score >= 15:
            return "C"

        return "D"

    @staticmethod
    def _decision(grade: str) -> str:

        mapping = {
            "A+": "РАЗРЕШИТЬ_МАКС_КАПИТАЛ",
            "A": "РАЗРЕШИТЬ",
            "B": "ОГРАНИЧЕННЫЙ_КАПИТАЛ",
            "C": "НАБЛЮДЕНИЕ",
            "D": "ОТКЛОНИТЬ",
            "N": "НЕДОСТАТОЧНО_ДАННЫХ",
        }

        return mapping.get(grade, "НАБЛЮДЕНИЕ")
