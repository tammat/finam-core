from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FORWARD_EDGE_SHADOW_TRADES_V1"
NAMESPACE = uuid.UUID("53ec1c83-5abd-4de8-a0b7-d87002c130a8")

DDL = """
CREATE TABLE IF NOT EXISTS analytics.forward_edge_shadow_trade_v1 (
    shadow_trade_id uuid PRIMARY KEY,
    observation_id uuid NOT NULL UNIQUE,
    cohort_id uuid NOT NULL,
    incubator_candidate_id uuid NOT NULL,
    hypothesis_id uuid NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    side text,
    signal_ts timestamptz NOT NULL,
    entry_ts timestamptz,
    exit_ts timestamptz,
    entry_price numeric,
    exit_price numeric,
    qty numeric NOT NULL DEFAULT 1,
    gross_pnl numeric,
    commission numeric,
    spread_cost numeric,
    slippage numeric,
    net_pnl numeric,
    shadow_status text NOT NULL,
    shadow_only boolean NOT NULL DEFAULT true,
    broker_order_sent boolean NOT NULL DEFAULT false,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    source_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_forward_edge_shadow_trade_v1_cohort_status
ON analytics.forward_edge_shadow_trade_v1(cohort_id,shadow_status,signal_ts DESC);
"""


def shadow_status(observation_status: str) -> str:
    return {"SIGNAL_PENDING_ENTRY": "PENDING_ENTRY", "OPEN": "OPEN", "CLOSED": "CLOSED"}.get(observation_status, "OBSERVING")


def main() -> int:
    inserted = updated = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                print("cohort=none")
                print("VERDICT=FORWARD_EDGE_SHADOW_TRADES_V1_NO_COHORT")
                return 0
            cohort_id = latest["cohort_id"]
            cur.execute("""
                SELECT observation_id,cohort_id,incubator_candidate_id,hypothesis_id,symbol,timeframe,
                       side,signal_ts,entry_ts,exit_ts,entry_price,exit_price,gross_pnl,
                       commission,spread_cost,slippage,net_pnl,observation_status
                FROM analytics.forward_edge_observation_v1 WHERE cohort_id=%s
                ORDER BY signal_ts,observation_id
            """, (cohort_id,))
            observations = cur.fetchall()
            for row in observations:
                shadow_trade_id = uuid.uuid5(NAMESPACE, str(row["observation_id"]))
                observation_id = str(row["observation_id"])
                cohort_id_value = str(row["cohort_id"])
                incubator_candidate_id = str(row["incubator_candidate_id"])
                hypothesis_id = str(row["hypothesis_id"])
                cur.execute("SELECT 1 FROM analytics.forward_edge_shadow_trade_v1 WHERE observation_id=%s", (observation_id,))
                exists = cur.fetchone() is not None
                cur.execute("""
                    INSERT INTO analytics.forward_edge_shadow_trade_v1 (
                        shadow_trade_id,observation_id,cohort_id,incubator_candidate_id,hypothesis_id,
                        symbol,timeframe,side,signal_ts,entry_ts,exit_ts,entry_price,exit_price,qty,
                        gross_pnl,commission,spread_cost,slippage,net_pnl,shadow_status,
                        shadow_only,broker_order_sent,runtime_allowed,execution_enabled,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,true,false,false,false,%s)
                    ON CONFLICT (observation_id) DO UPDATE SET
                        entry_ts=excluded.entry_ts,exit_ts=excluded.exit_ts,
                        entry_price=excluded.entry_price,exit_price=excluded.exit_price,
                        gross_pnl=excluded.gross_pnl,commission=excluded.commission,
                        spread_cost=excluded.spread_cost,slippage=excluded.slippage,
                        net_pnl=excluded.net_pnl,shadow_status=excluded.shadow_status,
                        shadow_only=true,broker_order_sent=false,runtime_allowed=false,
                        execution_enabled=false,source_version=excluded.source_version,updated_at=now()
                """, (
                    str(shadow_trade_id),observation_id,cohort_id_value,incubator_candidate_id,hypothesis_id,
                    row["symbol"],row["timeframe"],row["side"],row["signal_ts"],row["entry_ts"],row["exit_ts"],
                    row["entry_price"],row["exit_price"],row["gross_pnl"],row["commission"],row["spread_cost"],
                    row["slippage"],row["net_pnl"],shadow_status(str(row["observation_status"])),SOURCE_VERSION,
                ))
                updated += int(exists)
                inserted += int(not exists)

            cur.execute("""
                SELECT count(*) total,count(*) FILTER (WHERE shadow_status='PENDING_ENTRY') pending,
                       count(*) FILTER (WHERE shadow_status='OPEN') open,count(*) FILTER (WHERE shadow_status='CLOSED') closed,
                       coalesce(sum(net_pnl) FILTER (WHERE shadow_status='CLOSED'),0) net_pnl,
                       count(*) FILTER (WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe
                FROM analytics.forward_edge_shadow_trade_v1 WHERE cohort_id=%s
            """, (cohort_id,))
            summary = dict(cur.fetchone())

    print(f"cohort_id={cohort_id}")
    print(f"observations={len(observations)}")
    print(f"inserted={inserted}")
    print(f"updated={updated}")
    for key in ("total", "pending", "open", "closed", "net_pnl", "unsafe"):
        print(f"{key}={summary[key]}")
    print("broker_orders=0")
    print("VERDICT=FORWARD_EDGE_SHADOW_TRADES_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
