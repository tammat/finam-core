from __future__ import annotations

import hashlib
import itertools
import json
import os
import uuid

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "SWING_HYPOTHESIS_FACTORY_V4_DYNAMIC_ENTRY_EXIT"
NAMESPACE = uuid.UUID("66ee4a61-5af4-56dd-9f86-d7f77555a207")
MAX_CANDIDATES = int(os.getenv("SWING_HYPOTHESIS_MAX_CANDIDATES", "360"))


def canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def failure_context(cur) -> tuple[str | None, list[str]]:
    plan_id = os.getenv("SWING_SOURCE_PLAN_ID", "").strip()
    if plan_id:
        cur.execute("SELECT reason_summary FROM analytics.edge_next_research_plan_v1 WHERE plan_id=%s", (plan_id,))
    else:
        cur.execute("SELECT plan_id,reason_summary FROM analytics.edge_next_research_plan_v1 ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        return None, []
    return str(row.get("plan_id") or plan_id), sorted((row["reason_summary"] or {}).keys())


def price_grid(timeframe: str, failure_reasons: list[str]) -> dict[str, tuple[dict, str]]:
    cost_failure = "NEGATIVE_COST_ADJUSTED_EXPECTANCY" in failure_reasons
    holds = {"H1": [6, 12, 20], "H4": [3, 6, 10], "D1": [2, 4, 8]}[timeframe]
    thresholds = [20, 40, 80] if cost_failure else [0, 20, 40]
    return {
        "MOMENTUM": ({"lookback": [10, 20, 40], "holding_bars": holds,
                       "threshold_bps": thresholds, "direction": ["LONG", "SHORT"]}, "SWING_PRICE_V1"),
        "BREAKOUT": ({"lookback": [10, 20, 40], "holding_bars": holds,
                       "confirmation_bars": [1, 2]}, "SWING_PRICE_V1"),
    }


def db_contract_grids(cur, timeframe: str, failure_reasons: list[str]) -> dict[str, tuple[dict, str]]:
    cur.execute("""SELECT family_code,engine_code,parameter_grid
        FROM analytics.swing_research_contract_v2
        WHERE enabled AND (%s = '{}'::text[] OR failure_triggers && %s::text[])
        ORDER BY priority,family_code""", (failure_reasons, failure_reasons))
    contract_rows = cur.fetchall()
    holds = {"H1": [12, 20, 40], "H4": [6, 10, 20], "D1": [4, 8, 12]}[timeframe]
    result = {}
    cur.execute("""SELECT entry_policy,exit_policy FROM analytics.research_entry_exit_contract_v1
        WHERE scope_code='SWING' AND timeframe=%s AND enabled""", (timeframe,))
    entry_exit = cur.fetchone() or {}
    for row in contract_rows:
        grid = dict(row["parameter_grid"])
        grid["holding_bars"] = holds
        for key, value in {**(entry_exit.get("entry_policy") or {}), **(entry_exit.get("exit_policy") or {})}.items():
            grid[key] = value if isinstance(value, list) else [value]
        result[str(row["family_code"])] = (grid, str(row["engine_code"]))
    return result


def main() -> None:
    require_off_market_research_window("SWING_HYPOTHESIS_FACTORY_V1")
    factory_run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            source_plan_id, failure_reasons = failure_context(cur)
            cur.execute("""SELECT audit_run_id FROM analytics.swing_data_quality_gate_v1 ORDER BY created_at DESC LIMIT 1""")
            audit = cur.fetchone()
            cur.execute("""SELECT symbol,timeframe FROM analytics.swing_data_quality_gate_v1
                WHERE audit_run_id=%s AND quality_status='READY' ORDER BY symbol,timeframe""", (audit["audit_run_id"],))
            markets = [(row["symbol"], row["timeframe"]) for row in cur.fetchall()]
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.swing_hypothesis_factory_v1 (
                    factory_run_id uuid NOT NULL, hypothesis_id uuid NOT NULL,
                    strategy_family text NOT NULL, engine_code text NOT NULL,
                    symbol text NOT NULL, timeframe text NOT NULL, parameter_json jsonb NOT NULL,
                    train_end timestamptz NOT NULL, selection_end timestamptz NOT NULL,
                    validation_end timestamptz NOT NULL, final_oos_start timestamptz NOT NULL,
                    final_oos_commitment text NOT NULL, final_oos_opened boolean NOT NULL DEFAULT false,
                    hypothesis_state text NOT NULL DEFAULT 'LOCKED', multiple_testing_family text NOT NULL,
                    promotion_allowed boolean NOT NULL DEFAULT false, source_version text NOT NULL,
                    source_plan_id uuid, source_failure_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
                    created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(factory_run_id,hypothesis_id)
                );
                ALTER TABLE analytics.swing_hypothesis_factory_v1 ADD COLUMN IF NOT EXISTS source_plan_id uuid;
                ALTER TABLE analytics.swing_hypothesis_factory_v1 ADD COLUMN IF NOT EXISTS source_failure_reasons jsonb NOT NULL DEFAULT '[]'::jsonb;
                CREATE INDEX IF NOT EXISTS swing_hypothesis_factory_latest_idx
                    ON analytics.swing_hypothesis_factory_v1(created_at DESC,strategy_family,timeframe);
            """)
            candidates = []
            for symbol, timeframe in markets:
                price_grids = {**price_grid(timeframe, failure_reasons),
                               **db_contract_grids(cur, timeframe, failure_reasons)}
                for family, (grid, engine) in price_grids.items():
                    keys = list(grid)
                    for values in itertools.product(*(grid[key] for key in keys)):
                        candidates.append((family,engine,symbol,timeframe,dict(zip(keys,values))))
            relationships = (("IMOEX2","SBER@MISX"),("IMOEX2","LKOH@MISX"),("USDRUBF@RTSX","GAZP@MISX"),
                             ("BR_ROLLING@RTSX","LKOH@MISX"),("NG_ROLLING@RTSX","GAZP@MISX"))
            for timeframe in ("H1","H4","D1"):
                for source,target in relationships:
                    for lookback,hold in itertools.product((5,10,20),(2,4,8)):
                        candidates.append(("RELATIVE_STRENGTH","SWING_RELATIVE_STRENGTH_V1",target,timeframe,
                                           {"benchmark":source,"lookback":lookback,"holding_bars":hold}))
                    for impulse,lag,hold in itertools.product((1,3,6),(1,2,3),(2,4)):
                        candidates.append(("INTERMARKET_LEAD_LAG","SWING_LEAD_LAG_V1",target,timeframe,
                                           {"source":source,"impulse_bars":impulse,"lag_bars":lag,"holding_bars":hold}))
            # Deterministic balanced cap: equal quota by family and timeframe, never ranked on outcomes.
            selected = []
            groups = sorted({(row[0], row[3]) for row in candidates})
            quota = max(1, MAX_CANDIDATES // len(groups))
            for family, timeframe in groups:
                selected.extend([row for row in candidates if row[0] == family and row[3] == timeframe][:quota])
            for family,engine,symbol,timeframe,params in selected:
                cur.execute("""SELECT ts FROM analytics.swing_market_bars_v1
                    WHERE symbol=%s AND timeframe=%s ORDER BY ts""", (symbol,timeframe))
                timestamps = [row["ts"] for row in cur.fetchall()]
                if len(timestamps) < 250:
                    continue
                train_end = timestamps[int(len(timestamps)*0.40)]
                selection_end = timestamps[int(len(timestamps)*0.60)]
                validation_end = timestamps[int(len(timestamps)*0.80)-1]
                final_start = timestamps[int(len(timestamps)*0.80)]
                identity = {"family":family,"engine":engine,"symbol":symbol,"timeframe":timeframe,"parameters":params}
                identity_json = canon(identity)
                hypothesis_id = uuid.uuid5(NAMESPACE, identity_json)
                commitment = hashlib.sha256(canon({"hypothesis_id":str(hypothesis_id),"final_start":final_start.isoformat(),
                                                   "last_ts":timestamps[-1].isoformat(),"bars":len(timestamps)}).encode()).hexdigest()
                cur.execute("""INSERT INTO analytics.swing_hypothesis_factory_v1
                    (factory_run_id,hypothesis_id,strategy_family,engine_code,symbol,timeframe,parameter_json,
                     train_end,selection_end,validation_end,final_oos_start,final_oos_commitment,
                     final_oos_opened,hypothesis_state,multiple_testing_family,promotion_allowed,source_version,
                     source_plan_id,source_failure_reasons)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,'LOCKED',%s,false,%s,%s,%s)""",
                    (factory_run_id,str(hypothesis_id),family,engine,symbol,timeframe,psycopg2.extras.Json(params),
                     train_end,selection_end,validation_end,final_start,commitment,f"SWING_{family}_V1",SOURCE_VERSION,
                     source_plan_id,psycopg2.extras.Json(failure_reasons)))
            cur.execute("""SELECT strategy_family,count(*) AS candidates,count(*) FILTER(WHERE final_oos_opened) opened
                FROM analytics.swing_hypothesis_factory_v1 WHERE factory_run_id=%s GROUP BY 1 ORDER BY 1""", (factory_run_id,))
            summary = cur.fetchall()
    total = sum(int(row["candidates"]) for row in summary)
    print(f"factory_run_id={factory_run_id}")
    print(f"source_plan_id={source_plan_id or 'NONE'}")
    print(f"source_failure_reasons={','.join(failure_reasons) or 'NONE'}")
    for row in summary: print(f"family={row['strategy_family']} candidates={row['candidates']} final_opened={row['opened']}")
    print(f"candidates={total}")
    print("nested_split=40_20_20_20")
    print("final_oos_opened=0")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=SWING_HYPOTHESIS_FACTORY_V1_LOCKED")


if __name__ == "__main__": main()
