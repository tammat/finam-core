from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExitAlphaPolicy:
    strategy: str
    timeframe: str
    stop_atr: float
    take_atr: float
    trail_atr: float
    max_bars_held: int
    policy_name: str


def build_exit_alpha_policy(
    *,
    strategy: str,
    timeframe: str,
    profit_factor: float,
    expectancy: float,
    volatility_state: str,
) -> ExitAlphaPolicy:
    """
    Русский комментарий:
    Подбирает базовую exit-policy по качеству стратегии и режиму волатильности.
    v1 ничего не исполняет напрямую, только формирует исследовательскую политику выхода.
    """

    strategy_upper = strategy.upper()

    if volatility_state == "high":
        stop_atr = 1.2
        take_atr = 2.4
        trail_atr = 1.0
        max_bars_held = 18
    elif volatility_state == "normal":
        stop_atr = 1.0
        take_atr = 2.0
        trail_atr = 0.8
        max_bars_held = 24
    else:
        stop_atr = 0.8
        take_atr = 1.4
        trail_atr = 0.6
        max_bars_held = 12

    if profit_factor < 1.0 or expectancy <= 0:
        policy_name = "DEFENSIVE_EXIT_ALPHA_V1"
        take_atr *= 0.75
        max_bars_held = min(max_bars_held, 10)
    else:
        policy_name = "BALANCED_EXIT_ALPHA_V1"

    return ExitAlphaPolicy(
        strategy=strategy_upper,
        timeframe=timeframe.upper(),
        stop_atr=round(stop_atr, 4),
        take_atr=round(take_atr, 4),
        trail_atr=round(trail_atr, 4),
        max_bars_held=max_bars_held,
        policy_name=policy_name,
    )


@dataclass(frozen=True)
class ExitAlphaReplayResult:
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    trades: int
    old_total_pnl: float
    new_total_pnl: float
    old_expectancy: float
    new_expectancy: float
    old_profit_factor: float
    new_profit_factor: float
    delta_expectancy: float
    delta_profit_factor: float
    policy_name: str


def _profit_factor(pnls: list[float]) -> float:
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))
    if gross_loss == 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def apply_exit_alpha_policy_to_pnl(*, pnl: float, bars_held: int, policy: ExitAlphaPolicy) -> float:
    result = float(pnl)

    if policy.policy_name == "DEFENSIVE_EXIT_ALPHA_V1":
        if result < 0:
            result *= 0.70
        if bars_held > policy.max_bars_held:
            result *= 0.85

    return result


def replay_exit_alpha_policy(
    *,
    symbol: str,
    strategy: str,
    timeframe: str,
    trade_source: str,
    policy: ExitAlphaPolicy,
    trades: list[tuple[float, int]],
) -> ExitAlphaReplayResult:
    old_pnls = [float(pnl) for pnl, _ in trades]
    new_pnls = [
        apply_exit_alpha_policy_to_pnl(
            pnl=float(pnl),
            bars_held=int(bars_held or 0),
            policy=policy,
        )
        for pnl, bars_held in trades
    ]

    count = len(old_pnls)
    old_total = sum(old_pnls)
    new_total = sum(new_pnls)

    old_expectancy = old_total / count if count else 0.0
    new_expectancy = new_total / count if count else 0.0

    old_pf = _profit_factor(old_pnls)
    new_pf = _profit_factor(new_pnls)

    return ExitAlphaReplayResult(
        symbol=symbol,
        strategy=strategy.upper(),
        timeframe=timeframe.upper(),
        trade_source=trade_source,
        trades=count,
        old_total_pnl=round(old_total, 6),
        new_total_pnl=round(new_total, 6),
        old_expectancy=round(old_expectancy, 6),
        new_expectancy=round(new_expectancy, 6),
        old_profit_factor=round(old_pf, 6),
        new_profit_factor=round(new_pf, 6),
        delta_expectancy=round(new_expectancy - old_expectancy, 6),
        delta_profit_factor=round(new_pf - old_pf, 6),
        policy_name=policy.policy_name,
    )
