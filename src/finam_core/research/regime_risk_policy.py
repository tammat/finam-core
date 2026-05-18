from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimePerformance:
    regime: str
    trend: str
    volatility: str
    trades: int
    net_pnl: float
    expectancy: float
    winrate: float


@dataclass(frozen=True)
class RegimePolicyDecision:
    regime: str
    trend: str
    volatility: str
    decision: str
    risk_multiplier: float
    reason: str


class RegimeRiskPolicy:
    """Русский комментарий: формирует риск-политику по режимам рынка."""

    def decide(
        self,
        items: list[RegimePerformance],
        *,
        min_trades: int = 5,
        min_expectancy: float = 0.0,
        min_winrate_to_allow: float = 0.55,
        min_winrate_to_limit: float = 0.45,
    ) -> list[RegimePolicyDecision]:
        result: list[RegimePolicyDecision] = []

        for item in items:
            if item.trades < min_trades:
                result.append(
                    RegimePolicyDecision(
                        regime=item.regime,
                        trend=item.trend,
                        volatility=item.volatility,
                        decision="НЕДОСТАТОЧНО_ДАННЫХ",
                        risk_multiplier=0.0,
                        reason=f"trades={item.trades}<min_trades={min_trades}",
                    )
                )
                continue

            if item.expectancy <= min_expectancy:
                result.append(
                    RegimePolicyDecision(
                        regime=item.regime,
                        trend=item.trend,
                        volatility=item.volatility,
                        decision="ЗАПРЕТИТЬ",
                        risk_multiplier=0.0,
                        reason=f"expectancy={item.expectancy:.6f}<=min_expectancy={min_expectancy:.6f}",
                    )
                )
                continue

            if item.winrate < min_winrate_to_limit:
                result.append(
                    RegimePolicyDecision(
                        regime=item.regime,
                        trend=item.trend,
                        volatility=item.volatility,
                        decision="ЗАПРЕТИТЬ",
                        risk_multiplier=0.0,
                        reason=f"winrate={item.winrate:.4f}<min_winrate_to_limit={min_winrate_to_limit:.4f}",
                    )
                )
                continue

            if item.winrate >= min_winrate_to_allow and item.expectancy > 0:
                multiplier = 1.0
                decision = "РАЗРЕШИТЬ"
            else:
                multiplier = 0.5
                decision = "ОГРАНИЧИТЬ"

            result.append(
                RegimePolicyDecision(
                    regime=item.regime,
                    trend=item.trend,
                    volatility=item.volatility,
                    decision=decision,
                    risk_multiplier=multiplier,
                    reason=f"expectancy={item.expectancy:.6f};winrate={item.winrate:.4f};trades={item.trades}",
                )
            )

        return result
