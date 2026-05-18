from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchInstrumentCandidate:
    symbol: str
    trades: int
    net_pnl: float
    expectancy: float
    winrate: float
    score: float


@dataclass(frozen=True)
class ResearchPortfolioAllocation:
    symbol: str
    capital_weight: float
    risk_weight: float
    decision: str
    reason: str


class PortfolioResearchAllocator:
    """Русский комментарий: распределяет исследовательский капитал между отобранными инструментами."""

    def allocate(
        self,
        candidates: list[ResearchInstrumentCandidate],
        *,
        max_symbol_weight: float = 0.50,
        min_trades: int = 3,
        min_expectancy: float = 0.0,
    ) -> list[ResearchPortfolioAllocation]:
        eligible = [
            c for c in candidates
            if c.trades >= min_trades and c.expectancy > min_expectancy and c.score > 0
        ]

        if not eligible:
            return [
                ResearchPortfolioAllocation(
                    symbol=c.symbol,
                    capital_weight=0.0,
                    risk_weight=0.0,
                    decision="НЕ_РАСПРЕДЕЛЯТЬ",
                    reason="нет_подходящих_инструментов",
                )
                for c in candidates
            ]

        total_score = sum(c.score for c in eligible)

        result: list[ResearchPortfolioAllocation] = []

        for c in candidates:
            if c not in eligible:
                result.append(
                    ResearchPortfolioAllocation(
                        symbol=c.symbol,
                        capital_weight=0.0,
                        risk_weight=0.0,
                        decision="НЕ_РАСПРЕДЕЛЯТЬ",
                        reason="не_прошел_фильтр",
                    )
                )
                continue

            raw_weight = c.score / total_score
            weight = min(raw_weight, max_symbol_weight)

            result.append(
                ResearchPortfolioAllocation(
                    symbol=c.symbol,
                    capital_weight=round(weight, 6),
                    risk_weight=round(weight / max_symbol_weight, 6) if max_symbol_weight > 0 else 0.0,
                    decision="РАСПРЕДЕЛИТЬ",
                    reason=f"score={c.score:.6f};expectancy={c.expectancy:.6f};trades={c.trades}",
                )
            )

        return result
