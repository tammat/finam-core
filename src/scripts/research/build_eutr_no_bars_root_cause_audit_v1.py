#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import psycopg
from psycopg.rows import dict_row

SYMBOL = "EUTR@MISX"
ALIASES = ["EUTR@MISX", "EUTR"]

def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    rows = {
        "symbol": SYMBOL,
        "aliases_checked": ALIASES,
        "runtime_active_universe": [],
        "market_bars": [],
        "breakout_history_latest": [],
        "diagnosis": "UNKNOWN",
        "planned_action": "REVIEW",
    }

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select symbol, strategy, timeframe, priority, score, is_enabled, source, updated_at
                from runtime_active_universe
                where symbol = %s
                order by updated_at desc
                """,
                (SYMBOL,),
            )
            rows["runtime_active_universe"] = list(cur.fetchall())

            for alias in ALIASES:
                for tf in ["M1", "M5"]:
                    cur.execute(
                        """
                        select
                            %s as symbol_checked,
                            %s as timeframe_checked,
                            count(*)::int as bars,
                            min(ts) as first_ts,
                            max(ts) as last_ts
                        from market_bars
                        where symbol = %s
                          and timeframe = %s
                        """,
                        (alias, tf, alias, tf),
                    )
                    rows["market_bars"].append(dict(cur.fetchone()))

            cur.execute(
                """
                select symbol, timeframe, created_at, bar_ts, close, prev_high, status
                from analytics_multi_asset_breakout_row_v1
                where symbol = %s
                order by created_at desc
                limit 5
                """,
                (SYMBOL,),
            )
            rows["breakout_history_latest"] = list(cur.fetchall())

    has_runtime = any(r.get("is_enabled") for r in rows["runtime_active_universe"])
    m1_bars = sum(int(r["bars"] or 0) for r in rows["market_bars"] if r["timeframe_checked"] == "M1")
    m5_bars = sum(int(r["bars"] or 0) for r in rows["market_bars"] if r["timeframe_checked"] == "M5")

    if not has_runtime:
        diagnosis = "EUTR_NOT_ACTIVE_IN_RUNTIME_UNIVERSE"
        planned_action = "FIX_RUNTIME_UNIVERSE_FIRST"
    elif m1_bars == 0 and m5_bars == 0:
        diagnosis = "EUTR_MARKET_BARS_ABSENT"
        planned_action = "MOEX_BACKFILL_M1_THEN_AGGREGATE_M5"
    elif m1_bars > 0 and m5_bars == 0:
        diagnosis = "EUTR_M1_EXISTS_M5_MISSING"
        planned_action = "AGGREGATE_M1_TO_M5"
    elif m5_bars > 0:
        diagnosis = "EUTR_M5_EXISTS_WATCHER_RECHECK_REQUIRED"
        planned_action = "RERUN_WATCHER_AND_HISTORY"
    else:
        diagnosis = "EUTR_UNKNOWN_DATA_STATE"
        planned_action = "MANUAL_REVIEW"

    out = {
        "verdict": "EUTR_NO_BARS_ROOT_CAUSE_AUDIT_READY",
        "mode": "read_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "diagnosis": diagnosis,
        "planned_action": planned_action,
        "rows": rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print(f"DIAGNOSIS={diagnosis}")
    print(f"NEXT_REQUIRED={planned_action}")
    print("VERDICT=EUTR_NO_BARS_ROOT_CAUSE_AUDIT_READY")
    print("TEST_EUTR_NO_BARS_ROOT_CAUSE_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
