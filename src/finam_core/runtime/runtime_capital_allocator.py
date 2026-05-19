from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalAllocationDecision:
    allowed: bool
    risk_multiplier: float
    max_position_value: float
    reason: str


class RuntimeCapitalAllocator:
    """Русский комментарий: рассчитывает допустимый капитал на новый сигнал."""

    def allocate(
        self,
        *,
        equity: float,
        cash: float,
        margin_utilization_pct: float,
        free_margin: float = 0.0,
        drawdown: float,
        signal_score: float,
        risk_reward: float,
        correlation_pressure: int,
        runtime_severity: str,
        base_position_pct: float = 0.05,
        max_position_pct: float = 0.10,
    ) -> CapitalAllocationDecision:
        if equity <= 0:
            return CapitalAllocationDecision(False, 0.0, 0.0, "equity<=0")

        available_capital = max(float(cash or 0.0), float(free_margin or 0.0))

        if available_capital <= 0:
            return CapitalAllocationDecision(False, 0.0, 0.0, "available_capital<=0")

        if runtime_severity == "CRITICAL":
            return CapitalAllocationDecision(False, 0.0, 0.0, "runtime_severity=CRITICAL")

        if margin_utilization_pct >= 70:
            return CapitalAllocationDecision(False, 0.0, 0.0, "margin_utilization>=70")

        if abs(drawdown) >= equity * 0.05:
            return CapitalAllocationDecision(False, 0.0, 0.0, "drawdown>=5pct_equity")

        multiplier = 1.0

        if runtime_severity == "WARNING":
            multiplier *= 0.5

        if risk_reward < 1.5:
            multiplier *= 0.0
        elif risk_reward >= 2.0:
            multiplier *= 1.2

        if signal_score < 1.0:
            multiplier *= 0.5
        elif signal_score >= 3.0:
            multiplier *= 1.2

        if correlation_pressure >= 2:
            multiplier *= 0.5

        if multiplier <= 0:
            return CapitalAllocationDecision(False, 0.0, 0.0, "multiplier<=0")

        raw_position = equity * base_position_pct * multiplier
        max_position = equity * max_position_pct

        position_value = min(raw_position, max_position, available_capital)

        return CapitalAllocationDecision(
            allowed=position_value > 0,
            risk_multiplier=round(multiplier, 4),
            max_position_value=round(position_value, 2),
            reason=(
                f"equity={equity:.2f};cash={cash:.2f};free_margin={free_margin:.2f};available={available_capital:.2f};"
                f"severity={runtime_severity};rr={risk_reward:.2f};"
                f"score={signal_score:.2f};correlation_pressure={correlation_pressure};"
                f"multiplier={multiplier:.4f}"
            ),
        )
