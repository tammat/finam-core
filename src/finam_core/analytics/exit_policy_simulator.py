from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable


@dataclass(frozen=True)
class ExitPolicyInput:
    pnl: float
    mae: float
    mfe: float


@dataclass(frozen=True)
class ExitPolicyCandidate:
    name: str
    take_distance: float
    stop_distance: float


@dataclass(frozen=True)
class ExitPolicySimulationResult:
    policy_name: str
    take_distance: float
    stop_distance: float
    simulated_trades: int
    simulated_wins: int
    simulated_losses: int
    simulated_winrate: float
    simulated_net_pnl: float
    simulated_profit_factor: float
    simulated_max_drawdown: float
    simulated_avg_pnl: float
    simulated_sharpe_like: float


def simulate_exit_policy(
    samples: Iterable[ExitPolicyInput],
    candidate: ExitPolicyCandidate,
) -> ExitPolicySimulationResult:
    pnls: list[float] = []

    take = abs(float(candidate.take_distance))
    stop = -abs(float(candidate.stop_distance))

    for sample in samples:
        mfe = float(sample.mfe)
        mae = float(sample.mae)
        original_pnl = float(sample.pnl)

        if take > 0 and mfe >= take:
            simulated_pnl = take
        elif stop < 0 and mae <= stop:
            simulated_pnl = stop
        else:
            simulated_pnl = original_pnl

        pnls.append(simulated_pnl)

    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    net_pnl = sum(pnls)
    trades = len(pnls)
    avg_pnl = net_pnl / trades if trades else 0.0
    winrate = len(wins) / trades if trades else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)

    variance = sum((x - avg_pnl) ** 2 for x in pnls) / trades if trades else 0.0
    stdev = sqrt(variance)
    sharpe_like = avg_pnl / stdev if stdev > 0 else 0.0

    return ExitPolicySimulationResult(
        policy_name=candidate.name,
        take_distance=round(take, 10),
        stop_distance=round(stop, 10),
        simulated_trades=trades,
        simulated_wins=len(wins),
        simulated_losses=len(losses),
        simulated_winrate=round(winrate, 10),
        simulated_net_pnl=round(net_pnl, 10),
        simulated_profit_factor=round(profit_factor, 10),
        simulated_max_drawdown=round(max_drawdown, 10),
        simulated_avg_pnl=round(avg_pnl, 10),
        simulated_sharpe_like=round(sharpe_like, 10),
    )


def simulate_exit_policies(
    samples: Iterable[ExitPolicyInput],
    candidates: Iterable[ExitPolicyCandidate],
) -> list[ExitPolicySimulationResult]:
    sample_list = list(samples)

    return [
        simulate_exit_policy(sample_list, candidate)
        for candidate in candidates
    ]
