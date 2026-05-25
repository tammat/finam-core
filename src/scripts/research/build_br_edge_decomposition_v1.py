from __future__ import annotations

import os

import psycopg


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH base AS (
        SELECT
            tcs.symbol,
            tcs.strategy,
            tcs.timeframe,
            tcs.regime,
            tcs.trend,
            tcs.volatility,
            tcs.lifecycle_state,
            a.pnl
        FROM trade_context_snapshots tcs
        JOIN trade_attribution_v2 a
          ON a.closed_trade_id = tcs.closed_trade_id
        WHERE tcs.symbol = 'BRM6@RTSX'
          AND tcs.strategy = 'BR_CONSERVATIVE_BREAKOUT'
          AND tcs.context_quality = 'FULL'
          AND a.strategy = 'BR_CONSERVATIVE_BREAKOUT'
    )
    SELECT
        regime,
        trend,
        volatility,
        lifecycle_state,
        COUNT(*) AS trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) AS losses,
        ROUND(AVG(pnl)::numeric, 6) AS expectancy,
        ROUND(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)::numeric, 6) AS gross_profit,
        ROUND(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END))::numeric, 6) AS gross_loss,
        CASE
            WHEN ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)) = 0
            THEN NULL
            ELSE ROUND(
                (
                    SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
                    / ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END))
                )::numeric,
                6
            )
        END AS profit_factor
    FROM base
    GROUP BY regime, trend, volatility, lifecycle_state
    ORDER BY trades DESC, profit_factor DESC NULLS LAST;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    print("BR_EDGE_DECOMPOSITION_V1")
    print("regime | trend | volatility | lifecycle | trades | wins | losses | expectancy | gross_profit | gross_loss | pf")

    for row in rows:
        print(" | ".join("" if v is None else str(v) for v in row))

    print(f"BR_EDGE_DECOMPOSITION_V1_OK rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
