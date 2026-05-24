from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg

from finam_core.research.active_contract_lifecycle_filter import (
    is_active_contract_edge_confirmed,
)


@dataclass(frozen=True)
class RuntimeSelectionDecision:
    """Решение runtime-gate по связке strategy + root_symbol + regime."""

    allowed: bool
    reason: str
    strategy: str
    symbol: str
    root_symbol: str
    regime: str


def normalize_root_symbol(symbol: str) -> str:
    """Русский комментарий: нормализуем конкретный контракт до базового инструмента."""
    if symbol.startswith("NG") and symbol.endswith("@RTSX"):
        return "NG"
    if symbol.startswith("BR") and symbol.endswith("@RTSX"):
        return "BR"
    if symbol.startswith("USDRUB") and symbol.endswith("@RTSX"):
        return "USDRUB"
    return symbol


def active_symbol_for_root_symbol(root_symbol: str) -> str:
    """Русский комментарий: активный контракт для hard-check в runtime gate."""
    if root_symbol == "NG":
        return os.getenv("ACTIVE_NG_SYMBOL", "NGM6@RTSX")
    if root_symbol == "BR":
        return os.getenv("ACTIVE_BR_SYMBOL", "BRM6@RTSX")
    if root_symbol == "USDRUB":
        return os.getenv("ACTIVE_USDRUB_SYMBOL", "USDRUBF@RTSX")
    return root_symbol


class RuntimeSelectionGate:
    """Русский комментарий: read-only gate допуска стратегии в runtime."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def is_allowed(self, *, strategy: str, symbol: str, regime: str) -> RuntimeSelectionDecision:
        root_symbol = normalize_root_symbol(symbol)

        sql = """
        SELECT reason
        FROM strategy_selection_runtime_normalized
        WHERE strategy = %(strategy)s
          AND root_symbol = %(root_symbol)s
          AND regime = %(regime)s
          AND status = 'PROMOTED_RUNTIME'
        LIMIT 1;
        """

        stats_sql = """
        SELECT
            trades,
            avg_net_pnl,
            win_rate
        FROM closed_trade_quality_stats
        WHERE root_symbol = %(root_symbol)s
          AND symbol = %(active_symbol)s
          AND strategy = %(strategy)s
          AND timeframe = %(timeframe)s
        LIMIT 1;
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    {
                        "strategy": strategy,
                        "root_symbol": root_symbol,
                        "regime": regime,
                    },
                )
                row = cur.fetchone()

        if row:
            active_symbol = active_symbol_for_root_symbol(root_symbol)
            timeframe = os.getenv("ACTIVE_CONTRACT_TIMEFRAME", "M5")

            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        stats_sql,
                        {
                            "strategy": strategy,
                            "root_symbol": root_symbol,
                            "active_symbol": active_symbol,
                            "timeframe": timeframe,
                        },
                    )
                    stats = cur.fetchone()

            if stats is None:
                lifecycle_decision = is_active_contract_edge_confirmed(
                    root_symbol=root_symbol,
                    active_symbol=active_symbol,
                    strategy=strategy,
                    timeframe=timeframe,
                    trades=0,
                    avg_net_pnl=0.0,
                    win_rate=0.0,
                )
            else:
                trades, avg_net_pnl, win_rate = stats
                lifecycle_decision = is_active_contract_edge_confirmed(
                    root_symbol=root_symbol,
                    active_symbol=active_symbol,
                    strategy=strategy,
                    timeframe=timeframe,
                    trades=int(trades),
                    avg_net_pnl=float(avg_net_pnl),
                    win_rate=float(win_rate),
                )

            if lifecycle_decision.allowed:
                return RuntimeSelectionDecision(
                    allowed=True,
                    reason="Связка разрешена selection layer и подтверждена активным контрактом",
                    strategy=strategy,
                    symbol=symbol,
                    root_symbol=root_symbol,
                    regime=regime,
                )

            return RuntimeSelectionDecision(
                allowed=False,
                reason=(
                    "runtime_hard_check_rejected:"
                    f"{lifecycle_decision.reason}:"
                    f"active={active_symbol}:"
                    f"trades={lifecycle_decision.trades}:"
                    f"avg_net_pnl={lifecycle_decision.avg_net_pnl}:"
                    f"win_rate={lifecycle_decision.win_rate}"
                ),
                strategy=strategy,
                symbol=symbol,
                root_symbol=root_symbol,
                regime=regime,
            )

        return RuntimeSelectionDecision(
            allowed=False,
            reason="Связка не разрешена selection layer",
            strategy=strategy,
            symbol=symbol,
            root_symbol=root_symbol,
            regime=regime,
        )
