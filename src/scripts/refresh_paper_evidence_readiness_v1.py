#!/usr/bin/env python3
"""Refresh Paper evidence readiness from closed trades and versioned policy."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "research" / "swing_forward_shadow_policy_v1.json"


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    required_closed = int(policy["minimum_closed_per_timeframe"])
    required_sessions = int(policy["minimum_trading_sessions"])
    minimum_pf = float(policy["minimum_net_profit_factor"])
    minimum_expectancy = float(policy["minimum_net_expectancy"])
    policy_version = str(policy.get("version") or policy.get("policy_version") or POLICY_PATH.stem)

    database_url = os.environ.get("DATABASE_URL", "postgresql:///finam_core")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH ordered AS (
                    SELECT
                        COALESCE(NULLIF(regime, ''), 'UNKNOWN') AS regime,
                        COALESCE(NULLIF(timeframe, ''), 'UNKNOWN') AS timeframe,
                        COALESCE(exit_ts, closed_at, created_at) AS event_ts,
                        COALESCE(net_pnl, 0)::numeric AS net_pnl,
                        SUM(COALESCE(net_pnl, 0)::numeric) OVER (
                            PARTITION BY COALESCE(NULLIF(regime, ''), 'UNKNOWN'),
                                         COALESCE(NULLIF(timeframe, ''), 'UNKNOWN')
                            ORDER BY COALESCE(exit_ts, closed_at, created_at), id
                        ) AS equity
                    FROM public.closed_trades
                    WHERE COALESCE(exit_ts, closed_at, created_at) IS NOT NULL
                ), drawdowns AS (
                    SELECT *, MAX(equity) OVER (
                        PARTITION BY regime, timeframe ORDER BY event_ts
                    ) - equity AS drawdown
                    FROM ordered
                )
                SELECT
                    regime,
                    timeframe,
                    COUNT(*)::integer AS closed_trades,
                    COUNT(DISTINCT event_ts::date)::integer AS trading_sessions,
                    CASE WHEN ABS(SUM(net_pnl) FILTER (WHERE net_pnl < 0)) > 0
                         THEN SUM(net_pnl) FILTER (WHERE net_pnl > 0)
                              / ABS(SUM(net_pnl) FILTER (WHERE net_pnl < 0))
                    END AS net_profit_factor,
                    AVG(net_pnl) AS net_expectancy,
                    MAX(drawdown) AS max_drawdown
                FROM drawdowns
                GROUP BY regime, timeframe
                """
            )
            rows = cursor.fetchall()
            cursor.execute("DELETE FROM analytics.paper_evidence_readiness_v1")
            for regime, timeframe, closed, sessions, profit_factor, expectancy, drawdown in rows:
                ready = (
                    closed >= required_closed
                    and sessions >= required_sessions
                    and profit_factor is not None
                    and float(profit_factor) >= minimum_pf
                    and expectancy is not None
                    and float(expectancy) >= minimum_expectancy
                )
                cursor.execute(
                    """
                    INSERT INTO analytics.paper_evidence_readiness_v1 (
                        regime, timeframe, closed_trades, trading_sessions,
                        required_closed_trades, required_trading_sessions,
                        missing_closed_trades, missing_trading_sessions,
                        net_profit_factor, net_expectancy, max_drawdown,
                        evidence_ready, policy_version, refreshed_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    """,
                    (
                        regime, timeframe, closed, sessions,
                        required_closed, required_sessions,
                        max(required_closed - closed, 0),
                        max(required_sessions - sessions, 0),
                        profit_factor, expectancy, drawdown,
                        ready, policy_version,
                    ),
                )
        connection.commit()
    print(f"PAPER_EVIDENCE_READINESS_REFRESHED rows={len(rows)} policy={policy_version}")


if __name__ == "__main__":
    main()
