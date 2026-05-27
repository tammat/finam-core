from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeValidationResult:
    symbol: str
    strategy: str
    timeframe: str
    trades: int
    pnl: float
    wins: int
    losses: int
    winrate: float
    profit_factor: float
    expectancy: float
    status: str
    reason: str


class EdgeValidationEngine:
    """Русский комментарий: read-only engine оценки статистического преимущества стратегии."""

    def validate(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        pnls: list[float],
        min_trades: int = 30,
        min_profit_factor: float = 1.10,
        min_expectancy: float = 0.0,
    ) -> EdgeValidationResult:
        trades = len(pnls)
        total_pnl = sum(pnls)

        wins_list = [x for x in pnls if x > 0]
        losses_list = [x for x in pnls if x < 0]

        wins = len(wins_list)
        losses = len(losses_list)
        winrate = wins / trades if trades else 0.0

        gross_profit = sum(wins_list)
        gross_loss = abs(sum(losses_list))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        expectancy = total_pnl / trades if trades else 0.0

        if trades == 0:
            status = "NO_VALID_TRADES"
            reason = "нет валидных сделок"
        elif trades < min_trades:
            status = "LOW_SAMPLE"
            reason = f"малая выборка: {trades} < {min_trades}"
        elif profit_factor < min_profit_factor:
            status = "EDGE_WEAK"
            reason = f"PF ниже порога: {profit_factor:.4f} < {min_profit_factor:.4f}"
        elif expectancy <= min_expectancy:
            status = "EDGE_WEAK"
            reason = f"expectancy ниже порога: {expectancy:.6f} <= {min_expectancy:.6f}"
        else:
            status = "EDGE_OK"
            reason = "статистическое преимущество подтверждено базовыми порогами"

        return EdgeValidationResult(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            trades=trades,
            pnl=total_pnl,
            wins=wins,
            losses=losses,
            winrate=winrate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            status=status,
            reason=reason,
        )
