from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class EdgeStats:
    name: str
    trades: int
    net_pnl: float
    gross_profit: float
    gross_loss: float
    avg_pnl: float
    winrate: float
    profit_factor: float
    max_consecutive_losses: int
    max_drawdown: float


def _max_consecutive_losses(pnl_values: List[float]) -> int:
    current = 0
    max_seen = 0

    for pnl in pnl_values:
        if pnl < 0:
            current += 1
            max_seen = max(max_seen, current)
        else:
            current = 0

    return max_seen


def _max_drawdown(pnl_values: List[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0

    for pnl in pnl_values:
        equity += pnl
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    return max_dd


def build_edge_stats(name: str, pnl_values: Iterable[float]) -> EdgeStats:
    values = list(pnl_values)

    trades = len(values)
    net_pnl = sum(values)
    gross_profit = sum(x for x in values if x > 0)
    gross_loss = abs(sum(x for x in values if x < 0))
    wins = sum(1 for x in values if x > 0)

    avg_pnl = net_pnl / trades if trades else 0.0
    winrate = wins / trades if trades else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0

    return EdgeStats(
        name=name,
        trades=trades,
        net_pnl=net_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        avg_pnl=avg_pnl,
        winrate=winrate,
        profit_factor=profit_factor,
        max_consecutive_losses=_max_consecutive_losses(values),
        max_drawdown=_max_drawdown(values),
    )


def compare_validated_vs_all(
    all_pnl: Iterable[float],
    validated_pnl: Iterable[float],
    rejected_pnl: Iterable[float],
) -> List[EdgeStats]:
    return [
        build_edge_stats("ALL", all_pnl),
        build_edge_stats("VALIDATED_ONLY", validated_pnl),
        build_edge_stats("REJECTED", rejected_pnl),
    ]
