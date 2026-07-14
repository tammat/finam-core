from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FORWARD_EDGE_SHADOW_TRAILING_V1"
POLICY_CODE = "ATR_TRAIL_14_2_5"
ATR_LOOKBACK = 14
ATR_MULTIPLIER = 2.5
COMMISSION_BPS = 8.0
NAMESPACE = uuid.UUID("a9023ee1-1500-4cf5-8684-0213750e14e9")

DDL = """
CREATE TABLE IF NOT EXISTS analytics.forward_edge_shadow_exit_variant_v1 (
    variant_id uuid PRIMARY KEY,
    observation_id uuid NOT NULL,
    cohort_id uuid NOT NULL,
    incubator_candidate_id uuid NOT NULL,
    hypothesis_id uuid NOT NULL,
    policy_code text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    side text NOT NULL,
    entry_ts timestamptz NOT NULL,
    entry_price numeric NOT NULL,
    exit_ts timestamptz,
    exit_price numeric,
    atr_value numeric,
    initial_stop numeric,
    final_stop numeric,
    exit_reason text,
    gross_pnl numeric,
    commission numeric,
    spread_cost numeric NOT NULL DEFAULT 0,
    slippage numeric NOT NULL DEFAULT 0,
    net_pnl numeric,
    variant_status text NOT NULL,
    shadow_only boolean NOT NULL DEFAULT true,
    broker_order_sent boolean NOT NULL DEFAULT false,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    source_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(observation_id,policy_code)
);
CREATE INDEX IF NOT EXISTS idx_forward_edge_shadow_exit_variant_v1_cohort
ON analytics.forward_edge_shadow_exit_variant_v1(cohort_id,policy_code,variant_status,entry_ts DESC);
"""


def atr(bars: list[dict]) -> float | None:
    if len(bars) < ATR_LOOKBACK + 1:
        return None
    values = []
    for previous, current in zip(bars[-ATR_LOOKBACK - 1:-1], bars[-ATR_LOOKBACK:]):
        high, low, previous_close = float(current["high"]), float(current["low"]), float(previous["close"])
        values.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return sum(values) / len(values)


def build_variant_id(observation_id: object) -> str:
    """Return a deterministic PostgreSQL-adaptable UUID value."""
    return str(uuid.uuid5(NAMESPACE, f"{observation_id}:{POLICY_CODE}"))


def simulate(side: str, entry_price: float, atr_value: float, bars: list[dict], baseline_exit_ts) -> dict:
    direction = 1 if side == "LONG" else -1
    stop = entry_price - ATR_MULTIPLIER * atr_value if direction == 1 else entry_price + ATR_MULTIPLIER * atr_value
    initial_stop = stop
    exit_ts = exit_price = None
    reason = None
    for bar in bars:
        bar_open, high, low = float(bar["open"]), float(bar["high"]), float(bar["low"])
        if direction == 1 and low <= stop:
            exit_ts, exit_price, reason = bar["ts"], min(bar_open, stop), "TRAILING_STOP"
            break
        if direction == -1 and high >= stop:
            exit_ts, exit_price, reason = bar["ts"], max(bar_open, stop), "TRAILING_STOP"
            break
        stop = max(stop, high - ATR_MULTIPLIER * atr_value) if direction == 1 else min(stop, low + ATR_MULTIPLIER * atr_value)
        if baseline_exit_ts is not None and bar["ts"] >= baseline_exit_ts:
            exit_ts, exit_price, reason = bar["ts"], float(bar["close"]), "BASE_HORIZON"
            break
    return {"initial_stop": initial_stop, "final_stop": stop, "exit_ts": exit_ts, "exit_price": exit_price, "exit_reason": reason}


def main() -> int:
    processed = unavailable = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                print("cohort=none")
                print("VERDICT=FORWARD_EDGE_SHADOW_TRAILING_V1_NO_COHORT")
                return 0
            cohort_id = latest["cohort_id"]
            cur.execute("""
                SELECT observation_id,cohort_id,incubator_candidate_id,hypothesis_id,symbol,timeframe,
                       side,entry_ts,entry_price,exit_ts
                FROM analytics.forward_edge_observation_v1
                WHERE cohort_id=%s AND entry_ts IS NOT NULL AND entry_price IS NOT NULL AND side IN ('LONG','SHORT')
                ORDER BY entry_ts,observation_id
            """, (cohort_id,))
            observations = cur.fetchall()
            for row in observations:
                cur.execute("""
                    SELECT ts,open,high,low,close FROM public.market_bars
                    WHERE symbol=%s AND timeframe=%s AND ts<=%s
                    ORDER BY ts DESC LIMIT %s
                """, (row["symbol"], row["timeframe"], row["entry_ts"], ATR_LOOKBACK + 1))
                history = list(reversed(cur.fetchall()))
                atr_value = atr(history)
                if atr_value is None or atr_value <= 0:
                    unavailable += 1
                    continue
                cur.execute("""
                    SELECT ts,open,high,low,close FROM public.market_bars
                    WHERE symbol=%s AND timeframe=%s AND ts>%s
                    ORDER BY ts
                """, (row["symbol"], row["timeframe"], row["entry_ts"]))
                future = cur.fetchall()
                result = simulate(str(row["side"]), float(row["entry_price"]), atr_value, future, row["exit_ts"])
                exit_price = result["exit_price"]
                gross = None if exit_price is None else (exit_price - float(row["entry_price"])) * (1 if row["side"] == "LONG" else -1)
                commission = float(row["entry_price"]) * COMMISSION_BPS / 10000
                net = None if gross is None else gross - commission
                status = "CLOSED" if exit_price is not None else "OPEN"
                variant_id = build_variant_id(row["observation_id"])
                cur.execute("""
                    INSERT INTO analytics.forward_edge_shadow_exit_variant_v1 (
                        variant_id,observation_id,cohort_id,incubator_candidate_id,hypothesis_id,policy_code,
                        symbol,timeframe,side,entry_ts,entry_price,exit_ts,exit_price,atr_value,
                        initial_stop,final_stop,exit_reason,gross_pnl,commission,net_pnl,variant_status,
                        shadow_only,broker_order_sent,runtime_allowed,execution_enabled,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,false,false,false,%s)
                    ON CONFLICT (observation_id,policy_code) DO UPDATE SET
                        exit_ts=excluded.exit_ts,exit_price=excluded.exit_price,atr_value=excluded.atr_value,
                        initial_stop=excluded.initial_stop,final_stop=excluded.final_stop,exit_reason=excluded.exit_reason,
                        gross_pnl=excluded.gross_pnl,commission=excluded.commission,net_pnl=excluded.net_pnl,
                        variant_status=excluded.variant_status,shadow_only=true,broker_order_sent=false,
                        runtime_allowed=false,execution_enabled=false,source_version=excluded.source_version,updated_at=now()
                """, (
                    variant_id,row["observation_id"],row["cohort_id"],row["incubator_candidate_id"],row["hypothesis_id"],
                    POLICY_CODE,row["symbol"],row["timeframe"],row["side"],row["entry_ts"],row["entry_price"],
                    result["exit_ts"],exit_price,atr_value,result["initial_stop"],result["final_stop"],result["exit_reason"],
                    gross,commission,net,status,SOURCE_VERSION,
                ))
                processed += 1

            cur.execute("""
                SELECT count(*) total,count(*) FILTER (WHERE variant_status='OPEN') open,
                       count(*) FILTER (WHERE variant_status='CLOSED') closed,
                       count(*) FILTER (WHERE exit_reason='TRAILING_STOP') trailing_exits,
                       coalesce(sum(net_pnl) FILTER (WHERE variant_status='CLOSED'),0) net_pnl,
                       count(*) FILTER (WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe
                FROM analytics.forward_edge_shadow_exit_variant_v1 WHERE cohort_id=%s AND policy_code=%s
            """, (cohort_id, POLICY_CODE))
            summary = dict(cur.fetchone())

    print(f"cohort_id={cohort_id}")
    print(f"policy={POLICY_CODE}")
    print(f"atr_lookback={ATR_LOOKBACK}")
    print(f"atr_multiplier={ATR_MULTIPLIER}")
    print(f"processed={processed}")
    print(f"unavailable={unavailable}")
    for key in ("total", "open", "closed", "trailing_exits", "net_pnl", "unsafe"):
        print(f"{key}={summary[key]}")
    print("broker_orders=0")
    print("VERDICT=FORWARD_EDGE_SHADOW_TRAILING_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
