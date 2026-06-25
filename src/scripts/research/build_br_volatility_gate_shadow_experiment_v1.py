#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_V1

Research-only эксперимент по BR volatility gate.

Источник:
public.runtime_guard_pre_signal_block_audit_v1

Цель:
сохранить shadow-наблюдения, что произошло бы при shadow_threshold=0.0004,
без изменения Runtime, Execution, Orders, Fills и Micro Live.
"""

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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS research.br_volatility_gate_shadow_observation_v1 (
            observation_id BIGSERIAL PRIMARY KEY,
            ts TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT,
            timeframe TEXT,
            price NUMERIC,
            atr NUMERIC,
            atr_pct NUMERIC,
            current_threshold NUMERIC,
            shadow_threshold NUMERIC NOT NULL,
            current_decision TEXT NOT NULL,
            shadow_decision TEXT NOT NULL,
            block_reason TEXT,
            compression_ratio NUMERIC,
            regime TEXT,
            trend TEXT,
            volatility TEXT,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_br_vol_shadow_symbol_created_v1
        ON research.br_volatility_gate_shadow_observation_v1(symbol, created_at)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_br_vol_shadow_decision_created_v1
        ON research.br_volatility_gate_shadow_observation_v1(shadow_decision, created_at)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_br_vol_shadow_reason_created_v1
        ON research.br_volatility_gate_shadow_observation_v1(block_reason, created_at)
        """
    )


def save_observations(cur, symbol: str, lookback_hours: int, shadow_threshold: float) -> int:
    ensure_table(cur)

    cur.execute(
        """
        INSERT INTO research.br_volatility_gate_shadow_observation_v1 (
            ts,
            symbol,
            strategy,
            timeframe,
            price,
            atr,
            atr_pct,
            current_threshold,
            shadow_threshold,
            current_decision,
            shadow_decision,
            block_reason,
            compression_ratio,
            regime,
            trend,
            volatility,
            payload
        )
        SELECT
            src.ts,
            src.symbol,
            src.strategy,
            src.timeframe,
            src.price::numeric,
            src.atr::numeric,
            src.atr_pct::numeric,
            src.threshold::numeric AS current_threshold,
            %(shadow_threshold)s::numeric AS shadow_threshold,
            'BLOCK'::text AS current_decision,
            CASE
                WHEN src.atr_pct::numeric >= %(shadow_threshold)s::numeric THEN 'ALLOW'
                ELSE 'BLOCK'
            END AS shadow_decision,
            src.block_reason,
            src.compression_ratio::numeric,
            src.regime,
            src.trend,
            src.volatility,
            jsonb_build_object(
                'source_table', 'public.runtime_guard_pre_signal_block_audit_v1',
                'source_id', src.id,
                'source_block_type', src.block_type,
                'experiment', 'BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_V1',
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            ) AS payload
        FROM public.runtime_guard_pre_signal_block_audit_v1 src
        WHERE src.created_at > now() - (%(lookback_hours)s::text || ' hours')::interval
          AND src.symbol=%(symbol)s
          AND src.block_type IN ('VOL_LOW_BLOCK','COMPRESSION_WATCH')
          AND NOT EXISTS (
              SELECT 1
              FROM research.br_volatility_gate_shadow_observation_v1 dst
              WHERE (dst.payload->>'source_id')::bigint = src.id
          )
        """,
        {
            "symbol": symbol,
            "lookback_hours": lookback_hours,
            "shadow_threshold": shadow_threshold,
        },
    )
    return int(cur.rowcount)


def metrics(cur, symbol: str, lookback_hours: int) -> dict[str, Any]:
    cur.execute(
        """
        SELECT
            count(*)::bigint AS observations,
            sum(CASE WHEN current_decision='BLOCK' THEN 1 ELSE 0 END)::bigint AS current_block,
            sum(CASE WHEN shadow_decision='ALLOW' THEN 1 ELSE 0 END)::bigint AS shadow_allow,
            sum(CASE WHEN shadow_decision='BLOCK' THEN 1 ELSE 0 END)::bigint AS shadow_block,
            min(atr_pct) AS min_atr_pct,
            avg(atr_pct) AS avg_atr_pct,
            max(atr_pct) AS max_atr_pct,
            avg(current_threshold) AS avg_current_threshold,
            avg(shadow_threshold) AS avg_shadow_threshold
        FROM research.br_volatility_gate_shadow_observation_v1
        WHERE created_at > now() - (%s::text || ' hours')::interval
          AND symbol=%s
        """,
        (lookback_hours, symbol),
    )
    row = dict(cur.fetchone())

    cur.execute(
        """
        SELECT block_reason, count(*)::bigint AS cnt
        FROM research.br_volatility_gate_shadow_observation_v1
        WHERE created_at > now() - (%s::text || ' hours')::interval
          AND symbol=%s
        GROUP BY block_reason
        ORDER BY cnt DESC, block_reason
        """,
        (lookback_hours, symbol),
    )
    reasons = [dict(r) for r in cur.fetchall()]

    row["block_reasons"] = reasons
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRN6@RTSX")
    parser.add_argument("--lookback-hours", type=int, default=2)
    parser.add_argument("--shadow-threshold", type=float, default=0.0004)
    parser.add_argument("--save", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            saved_rows = 0
            if args.save:
                saved_rows = save_observations(
                    cur,
                    symbol=args.symbol,
                    lookback_hours=args.lookback_hours,
                    shadow_threshold=args.shadow_threshold,
                )
                conn.commit()
            else:
                ensure_table(cur)
                conn.rollback()

            m = metrics(cur, args.symbol, args.lookback_hours)

    observations = int(m["observations"] or 0)
    shadow_allow = int(m["shadow_allow"] or 0)
    shadow_block = int(m["shadow_block"] or 0)
    allow_ratio = 0.0 if observations == 0 else shadow_allow / observations

    print("=== BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"symbol={args.symbol}")
    print(f"lookback_hours={args.lookback_hours}")
    print(f"shadow_threshold={args.shadow_threshold}")
    print(f"saved_rows={saved_rows}")
    print(f"observations={observations}")
    print(f"current_block={int(m['current_block'] or 0)}")
    print(f"shadow_allow={shadow_allow}")
    print(f"shadow_block={shadow_block}")
    print(f"allow_ratio={allow_ratio:.6f}")
    print(f"avg_atr_pct={m['avg_atr_pct']}")
    print(f"avg_current_threshold={m['avg_current_threshold']}")
    print(f"avg_shadow_threshold={m['avg_shadow_threshold']}")

    for item in m["block_reasons"]:
        print(f"block_reason={item['block_reason']}|count={item['cnt']}")

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_READY")

    return 0


if __name__ == "__main__":
    sys.exit(main())
