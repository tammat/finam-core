#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRN6@RTSX")
    args = parser.parse_args()

    sql = """
        WITH base AS (
            SELECT
                s.symbol,
                s.side,
                s.horizon_bars,
                coalesce(o.block_reason,'UNKNOWN') AS block_reason,
                s.net_pnl,
                s.mfe,
                s.mae,
                s.outcome
            FROM research.br_volatility_gate_shadow_simulation_v1 s
            JOIN research.br_volatility_gate_shadow_observation_v1 o
              ON o.observation_id=s.observation_id
            WHERE s.symbol=%s
              AND s.outcome <> 'NO_EXIT_BAR'
        ),
        agg AS (
            SELECT
                symbol,
                side,
                horizon_bars,
                block_reason,
                count(*)::bigint AS trades,
                sum(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)::bigint AS wins,
                sum(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END)::bigint AS losses,
                sum(CASE WHEN net_pnl = 0 THEN 1 ELSE 0 END)::bigint AS flats,
                coalesce(sum(net_pnl),0) AS net_pnl,
                avg(net_pnl) AS expectancy,
                coalesce(sum(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0) AS gross_profit,
                abs(coalesce(sum(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END),0)) AS gross_loss,
                avg(mfe) AS avg_mfe,
                avg(mae) AS avg_mae
            FROM base
            GROUP BY symbol, side, horizon_bars, block_reason
        )
        SELECT
            symbol,
            side,
            horizon_bars,
            block_reason,
            trades,
            wins,
            losses,
            flats,
            round((wins::numeric / nullif(trades,0)), 6) AS winrate,
            round(net_pnl, 6) AS net_pnl,
            round(expectancy, 6) AS expectancy,
            CASE
                WHEN gross_loss = 0 AND gross_profit > 0 THEN NULL
                WHEN gross_loss = 0 THEN 0
                ELSE round(gross_profit / gross_loss, 6)
            END AS profit_factor,
            round(avg_mfe, 6) AS avg_mfe,
            round(avg_mae, 6) AS avg_mae
        FROM agg
        ORDER BY net_pnl DESC, profit_factor DESC NULLS LAST, trades DESC
    """

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (args.symbol,))
            rows = [dict(r) for r in cur.fetchall()]

    print("=== BR_VOLATILITY_GATE_SHADOW_SLICE_SCORECARD_V1 ===")
    print(f"symbol={args.symbol}")
    print(f"rows={len(rows)}")

    best = rows[0] if rows else None
    if best:
        print(
            "best_slice="
            f"{best['side']}|"
            f"h{best['horizon_bars']}|"
            f"{best['block_reason']}|"
            f"trades={best['trades']}|"
            f"net_pnl={best['net_pnl']}|"
            f"pf={best['profit_factor']}|"
            f"expectancy={best['expectancy']}"
        )

    for r in rows:
        print(
            "slice="
            f"{r['side']}|"
            f"h{r['horizon_bars']}|"
            f"{r['block_reason']}|"
            f"trades={r['trades']}|"
            f"wins={r['wins']}|"
            f"losses={r['losses']}|"
            f"flats={r['flats']}|"
            f"winrate={r['winrate']}|"
            f"net_pnl={r['net_pnl']}|"
            f"expectancy={r['expectancy']}|"
            f"pf={r['profit_factor']}|"
            f"avg_mfe={r['avg_mfe']}|"
            f"avg_mae={r['avg_mae']}"
        )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=BR_VOLATILITY_GATE_SHADOW_SLICE_SCORECARD_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
