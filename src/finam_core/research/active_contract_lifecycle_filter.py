from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActiveContractLifecycleDecision:
    """Русский комментарий: решение о переносе edge на активный контракт."""

    allowed: bool
    reason: str
    root_symbol: str
    active_symbol: str
    strategy: str
    timeframe: str
    trades: int
    avg_net_pnl: float
    win_rate: float


def is_active_contract_edge_confirmed(
    *,
    root_symbol: str,
    active_symbol: str,
    strategy: str,
    timeframe: str,
    trades: int,
    avg_net_pnl: float,
    win_rate: float,
    min_trades: int = 30,
    min_avg_net_pnl: float = 0.0,
    min_win_rate: float = 0.48,
) -> ActiveContractLifecycleDecision:
    """
    Русский комментарий:
    Запрещает перенос runtime promotion со старого контракта на новый,
    пока активный контракт сам не подтвердил edge.
    """
    if trades < min_trades:
        return ActiveContractLifecycleDecision(
            allowed=False,
            reason="active_contract_not_enough_trades",
            root_symbol=root_symbol,
            active_symbol=active_symbol,
            strategy=strategy,
            timeframe=timeframe,
            trades=trades,
            avg_net_pnl=avg_net_pnl,
            win_rate=win_rate,
        )

    if avg_net_pnl <= min_avg_net_pnl:
        return ActiveContractLifecycleDecision(
            allowed=False,
            reason="active_contract_negative_expectancy",
            root_symbol=root_symbol,
            active_symbol=active_symbol,
            strategy=strategy,
            timeframe=timeframe,
            trades=trades,
            avg_net_pnl=avg_net_pnl,
            win_rate=win_rate,
        )

    if win_rate < min_win_rate:
        return ActiveContractLifecycleDecision(
            allowed=False,
            reason="active_contract_low_win_rate",
            root_symbol=root_symbol,
            active_symbol=active_symbol,
            strategy=strategy,
            timeframe=timeframe,
            trades=trades,
            avg_net_pnl=avg_net_pnl,
            win_rate=win_rate,
        )

    return ActiveContractLifecycleDecision(
        allowed=True,
        reason="active_contract_edge_confirmed",
        root_symbol=root_symbol,
        active_symbol=active_symbol,
        strategy=strategy,
        timeframe=timeframe,
        trades=trades,
        avg_net_pnl=avg_net_pnl,
        win_rate=win_rate,
    )
