from __future__ import annotations

import json
import os
import statistics
import uuid
from pathlib import Path

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "SWING_FORWARD_SHADOW_ROUTER_V1"
ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path(
    os.getenv(
        "SWING_FORWARD_SHADOW_POLICY_CONFIG",
        ROOT / "config/research/swing_forward_shadow_policy_v1.json",
    )
)


def load_policy() -> dict:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy.get("policy_version") != "SWING_FORWARD_SHADOW_POLICY_V1":
        raise RuntimeError("SWING_FORWARD_SHADOW_POLICY_VERSION_INVALID")
    return policy

DDL = """
CREATE TABLE IF NOT EXISTS analytics.swing_shadow_observation_v1 (
    observation_id uuid PRIMARY KEY,
    swing_shadow_cohort_id uuid NOT NULL,
    swing_shadow_candidate_id uuid NOT NULL,
    hypothesis_id uuid NOT NULL,
    strategy_family text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    side text NOT NULL,
    signal_ts timestamptz NOT NULL,
    entry_ts timestamptz,
    entry_price numeric,
    holding_bars integer NOT NULL,
    fixed_exit_ts timestamptz,
    fixed_exit_price numeric,
    fixed_gross_pnl numeric,
    fixed_commission numeric,
    fixed_net_pnl numeric,
    atr_value numeric,
    trailing_stop numeric,
    trailing_exit_ts timestamptz,
    trailing_exit_price numeric,
    trailing_gross_pnl numeric,
    trailing_commission numeric,
    trailing_net_pnl numeric,
    trailing_exit_reason text,
    observation_status text NOT NULL,
    shadow_only boolean NOT NULL DEFAULT true,
    broker_order_sent boolean NOT NULL DEFAULT false,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    signal_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(swing_shadow_cohort_id,swing_shadow_candidate_id,signal_ts)
);
CREATE TABLE IF NOT EXISTS analytics.swing_shadow_worker_state_v1 (
    swing_shadow_cohort_id uuid NOT NULL,
    swing_shadow_candidate_id uuid NOT NULL,
    last_evaluated_ts timestamptz,
    worker_status text NOT NULL,
    last_error text,
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(swing_shadow_cohort_id,swing_shadow_candidate_id)
);
"""


def atr(bars: list[dict], lookback: int) -> float | None:
    if len(bars) < lookback + 1:
        return None
    values = []
    for previous, current in zip(bars[-lookback - 1:-1], bars[-lookback:]):
        high, low, previous_close = float(current["high"]), float(current["low"]), float(previous["close"])
        values.append(max(high-low,abs(high-previous_close),abs(low-previous_close)))
    return statistics.fmean(values)


def side_for(candidate: dict, target: list[dict], benchmark: list[dict] | None) -> str | None:
    params = candidate["frozen_parameter_json"]
    family = candidate["strategy_family"]
    lookback = int(params.get("lookback", params.get("impulse_bars", 20)))
    if len(target) < lookback + 1:
        return None
    closes = [float(row["close"]) for row in target]
    if family == "BREAKOUT":
        confirmation = int(params.get("confirmation_bars", 1))
        if len(closes) < lookback + confirmation:
            return None
        ceiling = max(closes[-lookback-confirmation:-confirmation])
        floor = min(closes[-lookback-confirmation:-confirmation])
        recent = closes[-confirmation:]
        return "LONG" if all(value > ceiling for value in recent) else ("SHORT" if all(value < floor for value in recent) else None)
    if family == "MOMENTUM":
        change = closes[-1] / closes[-lookback-1] - 1
        direction = str(params.get("direction") or "")
        side = "LONG" if change > 0 else ("SHORT" if change < 0 else None)
        return side if side and (not direction or side == direction) else None
    if benchmark and len(benchmark) >= lookback + 1:
        bench = [float(row["close"]) for row in benchmark]
        target_return = closes[-1] / closes[-lookback-1] - 1
        benchmark_return = bench[-1] / bench[-lookback-1] - 1
        if family == "RELATIVE_STRENGTH":
            relative = target_return - benchmark_return
            return "LONG" if relative > 0 else ("SHORT" if relative < 0 else None)
        return "LONG" if benchmark_return > 0 else ("SHORT" if benchmark_return < 0 else None)
    return None


def main() -> int:
    policy = load_policy()
    atr_lookback = int(policy["atr_lookback"])
    atr_multiplier = float(policy["atr_multiplier"])
    commission_bps = float(policy["commission_bps"])
    created = entered = closed = trailing_closed = unavailable = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute("SELECT swing_shadow_cohort_id FROM analytics.swing_shadow_cohort_v1 WHERE cohort_status='ACCUMULATING' ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                print("VERDICT=SWING_FORWARD_SHADOW_ROUTER_V1_NO_COHORT")
                return 1
            cohort_id = latest["swing_shadow_cohort_id"]
            cur.execute("SELECT * FROM analytics.swing_shadow_cohort_v1 WHERE swing_shadow_cohort_id=%s ORDER BY timeframe,strategy_family", (cohort_id,))
            candidates = cur.fetchall()
            for candidate in candidates:
                cur.execute("SELECT * FROM analytics.swing_shadow_observation_v1 WHERE swing_shadow_cohort_id=%s AND swing_shadow_candidate_id=%s AND observation_status IN ('PENDING_ENTRY','OPEN') ORDER BY signal_ts LIMIT 1", (cohort_id,candidate["swing_shadow_candidate_id"]))
                observation = cur.fetchone()
                cur.execute("SELECT ts,open,high,low,close FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s ORDER BY ts", (candidate["symbol"],candidate["timeframe"]))
                bars = cur.fetchall()
                if observation and observation["observation_status"] == "PENDING_ENTRY":
                    later = [bar for bar in bars if bar["ts"] > observation["signal_ts"]]
                    if later:
                        entry_bar = later[0]
                        history = [bar for bar in bars if bar["ts"] <= entry_bar["ts"]]
                        atr_value = atr(history, atr_lookback)
                        if atr_value:
                            entry_price = float(entry_bar["open"])
                            stop = entry_price - atr_multiplier*atr_value if observation["side"] == "LONG" else entry_price + atr_multiplier*atr_value
                            cur.execute("UPDATE analytics.swing_shadow_observation_v1 SET entry_ts=%s,entry_price=%s,atr_value=%s,trailing_stop=%s,observation_status='OPEN',updated_at=now() WHERE observation_id=%s", (entry_bar["ts"],entry_price,atr_value,stop,observation["observation_id"]))
                            entered += 1
                            cur.execute("SELECT * FROM analytics.swing_shadow_observation_v1 WHERE observation_id=%s", (observation["observation_id"],))
                            observation = cur.fetchone()
                        else:
                            unavailable += 1
                if observation and observation["observation_status"] == "OPEN":
                    later = [bar for bar in bars if bar["ts"] > observation["entry_ts"]]
                    stop = float(observation["trailing_stop"])
                    trail_exit_ts, trail_exit_price = observation["trailing_exit_ts"], observation["trailing_exit_price"]
                    for bar in later:
                        if trail_exit_ts is None:
                            if observation["side"] == "LONG" and float(bar["low"]) <= stop:
                                trail_exit_ts, trail_exit_price = bar["ts"], min(float(bar["open"]),stop)
                            elif observation["side"] == "SHORT" and float(bar["high"]) >= stop:
                                trail_exit_ts, trail_exit_price = bar["ts"], max(float(bar["open"]),stop)
                            if trail_exit_ts is None:
                                stop = max(stop,float(bar["high"])-atr_multiplier*float(observation["atr_value"])) if observation["side"] == "LONG" else min(stop,float(bar["low"])+atr_multiplier*float(observation["atr_value"]))
                    if trail_exit_ts is not None and observation["trailing_exit_ts"] is None:
                        direction = 1 if observation["side"] == "LONG" else -1
                        gross = (float(trail_exit_price)-float(observation["entry_price"]))*direction
                        commission = float(observation["entry_price"])*commission_bps/10000
                        cur.execute("UPDATE analytics.swing_shadow_observation_v1 SET trailing_stop=%s,trailing_exit_ts=%s,trailing_exit_price=%s,trailing_gross_pnl=%s,trailing_commission=%s,trailing_net_pnl=%s,trailing_exit_reason='ATR_TRAILING_STOP',updated_at=now() WHERE observation_id=%s", (stop,trail_exit_ts,trail_exit_price,gross,commission,gross-commission,observation["observation_id"]))
                        trailing_closed += 1
                    hold = int(observation["holding_bars"])
                    if len(later) >= hold:
                        exit_bar = later[hold-1]
                        direction = 1 if observation["side"] == "LONG" else -1
                        exit_price = float(exit_bar["close"])
                        gross = (exit_price-float(observation["entry_price"]))*direction
                        commission = float(observation["entry_price"])*commission_bps/10000
                        if trail_exit_ts is None:
                            trail_gross = gross
                            cur.execute("UPDATE analytics.swing_shadow_observation_v1 SET trailing_exit_ts=%s,trailing_exit_price=%s,trailing_gross_pnl=%s,trailing_commission=%s,trailing_net_pnl=%s,trailing_exit_reason='BASE_HORIZON' WHERE observation_id=%s", (exit_bar["ts"],exit_price,trail_gross,commission,trail_gross-commission,observation["observation_id"]))
                        cur.execute("UPDATE analytics.swing_shadow_observation_v1 SET fixed_exit_ts=%s,fixed_exit_price=%s,fixed_gross_pnl=%s,fixed_commission=%s,fixed_net_pnl=%s,observation_status='CLOSED',updated_at=now() WHERE observation_id=%s", (exit_bar["ts"],exit_price,gross,commission,gross-commission,observation["observation_id"]))
                        closed += 1
                        observation = None
                cur.execute("SELECT last_evaluated_ts FROM analytics.swing_shadow_worker_state_v1 WHERE swing_shadow_cohort_id=%s AND swing_shadow_candidate_id=%s", (cohort_id,candidate["swing_shadow_candidate_id"]))
                state = cur.fetchone()
                last = state["last_evaluated_ts"] if state and state["last_evaluated_ts"] else candidate["observation_not_before"]
                new_bars = [bar for bar in bars if bar["ts"] > last]
                if not observation and new_bars:
                    latest_bar = new_bars[-1]
                    target = [bar for bar in bars if bar["ts"] <= latest_bar["ts"]]
                    params = candidate["frozen_parameter_json"]
                    benchmark_symbol = params.get("benchmark") or params.get("source")
                    benchmark = None
                    if benchmark_symbol:
                        cur.execute("SELECT ts,open,high,low,close FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s AND ts<=%s ORDER BY ts", (benchmark_symbol,candidate["timeframe"],latest_bar["ts"]))
                        benchmark = cur.fetchall()
                    side = side_for(candidate,target,benchmark)
                    if side:
                        context = {"benchmark":benchmark_symbol,"parameters":params,"final_oos_opened":False}
                        cur.execute("""INSERT INTO analytics.swing_shadow_observation_v1
                            (observation_id,swing_shadow_cohort_id,swing_shadow_candidate_id,hypothesis_id,strategy_family,
                             symbol,timeframe,side,signal_ts,holding_bars,observation_status,shadow_only,
                             broker_order_sent,runtime_allowed,execution_enabled,signal_context,source_version)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING_ENTRY',true,false,false,false,%s::jsonb,%s)
                            ON CONFLICT DO NOTHING""", (str(uuid.uuid4()),str(cohort_id),str(candidate["swing_shadow_candidate_id"]),
                            str(candidate["hypothesis_id"]),candidate["strategy_family"],candidate["symbol"],candidate["timeframe"],
                            side,latest_bar["ts"],int(params.get("holding_bars",6)),json.dumps(context),SOURCE_VERSION))
                        created += cur.rowcount
                latest_ts = bars[-1]["ts"] if bars else last
                cur.execute("""INSERT INTO analytics.swing_shadow_worker_state_v1 VALUES(%s,%s,%s,'OK',NULL,%s,now())
                    ON CONFLICT(swing_shadow_cohort_id,swing_shadow_candidate_id) DO UPDATE SET
                    last_evaluated_ts=excluded.last_evaluated_ts,worker_status='OK',last_error=NULL,source_version=excluded.source_version,updated_at=now()""",
                    (str(cohort_id),str(candidate["swing_shadow_candidate_id"]),latest_ts,SOURCE_VERSION))

            cur.execute("""SELECT count(*) total,count(*) FILTER(WHERE observation_status='PENDING_ENTRY') pending,
                count(*) FILTER(WHERE observation_status='OPEN') open,count(*) FILTER(WHERE observation_status='CLOSED') closed,
                count(*) FILTER(WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe
                FROM analytics.swing_shadow_observation_v1 WHERE swing_shadow_cohort_id=%s""", (cohort_id,))
            summary = dict(cur.fetchone())
    print(f"cohort_id={cohort_id}")
    print(f"candidates={len(candidates)}")
    print(f"signals_created={created}")
    print(f"entries_created={entered}")
    print(f"fixed_closed={closed}")
    print(f"trailing_closed={trailing_closed}")
    print(f"total={summary['total']}")
    print(f"pending={summary['pending']}")
    print(f"open={summary['open']}")
    print(f"closed={summary['closed']}")
    print(f"unsafe={summary['unsafe']}")
    print("broker_orders=0")
    print("final_oos_opened=0")
    print("VERDICT=SWING_FORWARD_SHADOW_ROUTER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
