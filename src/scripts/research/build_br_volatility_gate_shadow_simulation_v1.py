#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_table(cur) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS research")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS research.br_volatility_gate_shadow_simulation_v1 (
            simulation_id BIGSERIAL PRIMARY KEY,
            observation_id BIGINT NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT,
            timeframe TEXT,
            side TEXT NOT NULL,
            entry_ts TIMESTAMPTZ NOT NULL,
            entry_price NUMERIC NOT NULL,
            horizon_bars INTEGER NOT NULL,
            exit_ts TIMESTAMPTZ,
            exit_price NUMERIC,
            gross_pnl NUMERIC,
            commission NUMERIC NOT NULL DEFAULT 0,
            net_pnl NUMERIC,
            mfe NUMERIC,
            mae NUMERIC,
            outcome TEXT NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_br_vol_shadow_sim_obs_side_horizon_v1
        ON research.br_volatility_gate_shadow_simulation_v1(observation_id, side, horizon_bars)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_br_vol_shadow_sim_symbol_created_v1
        ON research.br_volatility_gate_shadow_simulation_v1(symbol, created_at)
    """)


def save_simulations(cur, symbol: str, horizons: list[int]) -> int:
    ensure_table(cur)

    values_sql = ",".join([f"({int(h)})" for h in horizons])

    sql = f"""
        WITH horizons(horizon_bars) AS (
            VALUES {values_sql}
        ),
        sides(side) AS (
            VALUES ('BUY'), ('SELL')
        ),
        source AS (
            SELECT
                o.observation_id,
                o.ts AS entry_ts,
                o.symbol,
                o.strategy,
                o.timeframe,
                o.price::numeric AS entry_price
            FROM research.br_volatility_gate_shadow_observation_v1 o
            WHERE o.symbol = %(symbol)s
              AND o.shadow_decision = 'ALLOW'
        ),
        expanded AS (
            SELECT
                s.*,
                sd.side,
                h.horizon_bars
            FROM source s
            CROSS JOIN sides sd
            CROSS JOIN horizons h
        ),
        bars_ranked AS (
            SELECT
                e.observation_id,
                e.side,
                e.horizon_bars,
                b.ts,
                b.high::numeric AS high,
                b.low::numeric AS low,
                b.close::numeric AS close,
                row_number() OVER (
                    PARTITION BY e.observation_id, e.side, e.horizon_bars
                    ORDER BY b.ts
                ) AS rn
            FROM expanded e
            JOIN public.market_bars b
              ON b.symbol = e.symbol
             AND b.ts > e.entry_ts
        ),
        exit_bar AS (
            SELECT
                observation_id,
                side,
                horizon_bars,
                ts AS exit_ts,
                close AS exit_price
            FROM bars_ranked
            WHERE rn = horizon_bars
        ),
        range_bar AS (
            SELECT
                observation_id,
                side,
                horizon_bars,
                max(high) AS max_high,
                min(low) AS min_low
            FROM bars_ranked
            WHERE rn <= horizon_bars
            GROUP BY observation_id, side, horizon_bars
        ),
        calc AS (
            SELECT
                e.observation_id,
                e.symbol,
                e.strategy,
                e.timeframe,
                e.side,
                e.entry_ts,
                e.entry_price,
                e.horizon_bars,
                xb.exit_ts,
                xb.exit_price,
                CASE
                    WHEN xb.exit_price IS NULL THEN NULL
                    WHEN e.side='BUY' THEN xb.exit_price - e.entry_price
                    ELSE e.entry_price - xb.exit_price
                END AS gross_pnl,
                0::numeric AS commission,
                CASE
                    WHEN xb.exit_price IS NULL THEN NULL
                    WHEN e.side='BUY' THEN xb.exit_price - e.entry_price
                    ELSE e.entry_price - xb.exit_price
                END AS net_pnl,
                CASE
                    WHEN xb.exit_price IS NULL THEN NULL
                    WHEN e.side='BUY' THEN rb.max_high - e.entry_price
                    ELSE e.entry_price - rb.min_low
                END AS mfe,
                CASE
                    WHEN xb.exit_price IS NULL THEN NULL
                    WHEN e.side='BUY' THEN rb.min_low - e.entry_price
                    ELSE e.entry_price - rb.max_high
                END AS mae
            FROM expanded e
            LEFT JOIN exit_bar xb
              ON xb.observation_id=e.observation_id
             AND xb.side=e.side
             AND xb.horizon_bars=e.horizon_bars
            LEFT JOIN range_bar rb
              ON rb.observation_id=e.observation_id
             AND rb.side=e.side
             AND rb.horizon_bars=e.horizon_bars
        )
        INSERT INTO research.br_volatility_gate_shadow_simulation_v1 (
            observation_id,
            symbol,
            strategy,
            timeframe,
            side,
            entry_ts,
            entry_price,
            horizon_bars,
            exit_ts,
            exit_price,
            gross_pnl,
            commission,
            net_pnl,
            mfe,
            mae,
            outcome,
            payload
        )
        SELECT
            c.observation_id,
            c.symbol,
            c.strategy,
            c.timeframe,
            c.side,
            c.entry_ts,
            c.entry_price,
            c.horizon_bars,
            c.exit_ts,
            c.exit_price,
            c.gross_pnl,
            c.commission,
            c.net_pnl,
            c.mfe,
            c.mae,
            CASE
                WHEN c.net_pnl IS NULL THEN 'NO_EXIT_BAR'
                WHEN c.net_pnl > 0 THEN 'WIN'
                WHEN c.net_pnl < 0 THEN 'LOSS'
                ELSE 'FLAT'
            END AS outcome,
            jsonb_build_object(
                'experiment', 'BR_VOLATILITY_GATE_SHADOW_SIMULATION_V1',
                'direction_mode', 'BOTH_SIDES_COUNTERFACTUAL',
                'commission_mode', 'ZERO_FOR_V1',
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            )
        FROM calc c
        ON CONFLICT (observation_id, side, horizon_bars) DO NOTHING
    """
    cur.execute(sql, {"symbol": symbol})
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRN6@RTSX")
    parser.add_argument("--horizons", default="3,5,10,15")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                saved_rows = save_simulations(cur, args.symbol, horizons)
                conn.commit()
            else:
                ensure_table(cur)
                conn.rollback()
                saved_rows = 0

            cur.execute("""
                SELECT
                    count(*)::bigint AS rows_total,
                    sum(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)::bigint AS wins,
                    sum(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END)::bigint AS losses,
                    sum(CASE WHEN outcome='FLAT' THEN 1 ELSE 0 END)::bigint AS flats,
                    sum(CASE WHEN outcome='NO_EXIT_BAR' THEN 1 ELSE 0 END)::bigint AS no_exit,
                    coalesce(sum(net_pnl),0) AS net_pnl
                FROM research.br_volatility_gate_shadow_simulation_v1
                WHERE symbol=%s
            """, (args.symbol,))
            m = dict(cur.fetchone())

    print("=== BR_VOLATILITY_GATE_SHADOW_SIMULATION_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"symbol={args.symbol}")
    print(f"horizons={','.join(map(str, horizons))}")
    print(f"saved_rows={saved_rows}")
    print(f"rows_total={m['rows_total']}")
    print(f"wins={m['wins']}")
    print(f"losses={m['losses']}")
    print(f"flats={m['flats']}")
    print(f"no_exit={m['no_exit']}")
    print(f"net_pnl={m['net_pnl']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=BR_VOLATILITY_GATE_SHADOW_SIMULATION_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
