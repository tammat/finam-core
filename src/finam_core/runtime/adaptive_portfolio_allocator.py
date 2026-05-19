from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioAllocationDecision:
    symbol: str
    allowed: bool

    allocated_capital: float
    allocated_qty: int

    quality_score: float
    grade: str

    reason: str


class AdaptivePortfolioAllocator:
    """Русский комментарий: institutional portfolio allocator."""

    def allocate(
        self,
        *,
        symbol: str,
        entry_price: float,

        quality_score: float,
        quality_grade: str,

        expected_value: float,

        available_capital: float,
        portfolio_heat: float,

        correlation_pressure: int,
        existing_position: bool,

        max_capital_pct: float = 0.10,
    ) -> PortfolioAllocationDecision:

        if existing_position:
            return PortfolioAllocationDecision(
                symbol=symbol,
                allowed=False,
                allocated_capital=0.0,
                allocated_qty=0,
                quality_score=quality_score,
                grade=quality_grade,
                reason="existing_position",
            )

        if expected_value <= 0:
            return PortfolioAllocationDecision(
                symbol=symbol,
                allowed=False,
                allocated_capital=0.0,
                allocated_qty=0,
                quality_score=quality_score,
                grade=quality_grade,
                reason="expected_value<=0",
            )

        if correlation_pressure >= 2:
            return PortfolioAllocationDecision(
                symbol=symbol,
                allowed=False,
                allocated_capital=0.0,
                allocated_qty=0,
                quality_score=quality_score,
                grade=quality_grade,
                reason="correlation_pressure>=2",
            )

        heat_multiplier = 1.0

        if portfolio_heat >= 0.70:
            heat_multiplier *= 0.4
        elif portfolio_heat >= 0.50:
            heat_multiplier *= 0.7

        quality_multiplier = 1.0

        if quality_grade == "A":
            quality_multiplier = 1.5
        elif quality_grade == "B":
            quality_multiplier = 1.2
        elif quality_grade == "C":
            quality_multiplier = 0.8
        else:
            quality_multiplier = 0.5

        raw_capital = (
            available_capital
            * max_capital_pct
            * heat_multiplier
            * quality_multiplier
        )

        allocated_capital = min(
            raw_capital,
            available_capital,
        )

        qty = 0

        if entry_price > 0:
            qty = int(allocated_capital / entry_price)

        if qty <= 0:
            return PortfolioAllocationDecision(
                symbol=symbol,
                allowed=False,
                allocated_capital=0.0,
                allocated_qty=0,
                quality_score=quality_score,
                grade=quality_grade,
                reason="qty<=0",
            )

        allocated_capital = qty * entry_price

        return PortfolioAllocationDecision(
            symbol=symbol,
            allowed=True,
            allocated_capital=round(allocated_capital, 2),
            allocated_qty=qty,
            quality_score=quality_score,
            grade=quality_grade,
            reason=(
                f"quality={quality_grade};"
                f"quality_score={quality_score:.2f};"
                f"portfolio_heat={portfolio_heat:.2f};"
                f"heat_multiplier={heat_multiplier:.2f};"
                f"quality_multiplier={quality_multiplier:.2f}"
            ),
        )
