from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EdgeBucket:
    symbol: str
    profile: str
    trades: int
    wins: int
    losses: int
    gross_pnl: float
    avg_pnl: float
    winrate: float


def build_edge_bucket(
    symbol: str,
    profile: str,
    pnl_values: Iterable[float],
) -> EdgeBucket:
    values = list(pnl_values)

    trades = len(values)
    wins = sum(1 for x in values if x > 0)
    losses = sum(1 for x in values if x < 0)

    gross_pnl = sum(values)

    avg_pnl = gross_pnl / trades if trades else 0.0
    winrate = wins / trades if trades else 0.0

    return EdgeBucket(
        symbol=symbol,
        profile=profile,
        trades=trades,
        wins=wins,
        losses=losses,
        gross_pnl=gross_pnl,
        avg_pnl=avg_pnl,
        winrate=winrate,
    )
