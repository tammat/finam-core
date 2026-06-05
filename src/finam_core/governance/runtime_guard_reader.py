from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import os
import psycopg2
import psycopg2.extras


GuardKey = Tuple[str, str, str, str, str]


@dataclass(frozen=True, slots=True)
class RuntimeGuardState:
    symbol: str
    strategy: str
    timeframe: str
    side: str
    session_bucket: str
    decision: str
    reason: str
    total_trades: int
    stop_trades: int
    stop_net_pnl: float
    take_trades: int
    take_net_pnl: float


class RuntimeGuardReader:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def load_active_guards(self) -> Dict[GuardKey, RuntimeGuardState]:
        sql = """
            select
                symbol,
                strategy,
                timeframe,
                side,
                session_bucket,
                decision,
                reason,
                total_trades,
                stop_trades,
                stop_net_pnl,
                take_trades,
                take_net_pnl
            from strategy_session_exit_guard_state
            where decision in ('BLOCK_STOP_DOMINATED', 'WATCH_NEGATIVE_TOTAL', 'ALLOW_WATCH')
            order by symbol, strategy, timeframe, side, session_bucket
        """

        result: Dict[GuardKey, RuntimeGuardState] = {}

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        for row in rows:
            state = RuntimeGuardState(
                symbol=row["symbol"],
                strategy=row["strategy"],
                timeframe=row["timeframe"],
                side=row["side"],
                session_bucket=row["session_bucket"],
                decision=row["decision"],
                reason=row["reason"],
                total_trades=int(row["total_trades"] or 0),
                stop_trades=int(row["stop_trades"] or 0),
                stop_net_pnl=float(row["stop_net_pnl"] or 0),
                take_trades=int(row["take_trades"] or 0),
                take_net_pnl=float(row["take_net_pnl"] or 0),
            )
            key = (
                state.symbol,
                state.strategy,
                state.timeframe,
                state.side,
                state.session_bucket,
            )
            result[key] = state

        return result
