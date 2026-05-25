from __future__ import annotations

import os
import psycopg


MIN_TRADES = 10
MIN_KEEP_PF = 1.10
MIN_KEEP_EXPECTANCY = 0.0


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH base AS (
        SELECT
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
          AND a.strategy = 'BR_CONSERVATIVE_BREAKOUT'
          AND tcs.context_quality = 'FULL'
    ),
    agg AS (
        SELECT
            regime,
            trend,
            volatility,
            lifecycle_state,
            COUNT(*) AS trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) AS losses,
            AVG(pnl) AS expectancy,
            SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) AS gross_profit,
            ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)) AS gross_loss
        FROM base
        GROUP BY regime, trend, volatility, lifecycle_state
    )
    SELECT
        regime,
        trend,
        volatility,
        lifecycle_state,
        trades,
        wins,
        losses,
        ROUND(expectancy::numeric, 6) AS expectancy,
        ROUND(gross_profit::numeric, 6) AS gross_profit,
        ROUND(gross_loss::numeric, 6) AS gross_loss,
        CASE
            WHEN gross_loss = 0 THEN NULL
            ELSE ROUND((gross_profit / gross_loss)::numeric, 6)
        END AS profit_factor
    FROM agg
    ORDER BY trades DESC, profit_factor DESC NULLS LAST;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    print("BR_REGIME_FILTER_CANDIDATES_V1")
    print(
        "regime | trend | volatility | lifecycle | trades | wins | losses | "
        "expectancy | gross_profit | gross_loss | pf | action | reason"
    )

    keep = 0
    downweight = 0
    block = 0

    for row in rows:
        (
            regime,
            trend,
            volatility,
            lifecycle,
            trades,
            wins,
            losses,
            expectancy,
            gross_profit,
            gross_loss,
            pf,
        ) = row

        trades_i = int(trades or 0)
        exp_f = float(expectancy or 0.0)
        pf_f = float(pf or 0.0)

        if trades_i >= MIN_TRADES and pf_f >= MIN_KEEP_PF and exp_f > MIN_KEEP_EXPECTANCY:
            action = "KEEP_RESEARCH_CLUSTER"
            reason = "cluster_edge_confirmed"
            keep += 1
        elif trades_i < MIN_TRADES:
            action = "DOWNWEIGHT_LOW_SAMPLE"
            reason = "sample_too_small"
            downweight += 1
        else:
            action = "BLOCK_CLUSTER"
            reason = "cluster_edge_not_confirmed"
            block += 1

        print(
            f"{regime} | {trend} | {volatility} | {lifecycle} | "
            f"{trades} | {wins} | {losses} | {expectancy} | "
            f"{gross_profit} | {gross_loss} | {pf or ''} | {action} | {reason}"
        )

    print(
        "BR_REGIME_FILTER_CANDIDATES_V1_OK "
        f"rows={len(rows)} keep={keep} downweight={downweight} block={block}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
