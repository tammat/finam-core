#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import psycopg2
import psycopg2.extras

RECOMMENDED_LIMIT = 8

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select symbol, strategy, score::numeric as score, priority, source
                from dynamic_watchlist
                where symbol like '%@MISX'
                order by priority desc nulls last, score desc nulls last, symbol
            """)
            dyn = [dict(r) for r in cur.fetchall()]

    selected_5 = dyn[:5]
    selected_8 = dyn[:8]

    added_by_8 = [
        r for r in selected_8
        if r["symbol"] not in {x["symbol"] for x in selected_5}
    ]

    out = {
        "verdict": "RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_READY",
        "mode": "plan_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "current_limit": 5,
        "recommended_limit": RECOMMENDED_LIMIT,
        "implementation": {
            "preferred": "set_env_only",
            "env_vars": {
                "RUNTIME_ACTIVE_UNIVERSE_LIMIT": str(RECOMMENDED_LIMIT),
                "RUNTIME_MAX_SYMBOLS": str(RECOMMENDED_LIMIT),
            },
            "do_not_change_code_defaults": True,
            "do_not_enable_execution": True,
            "do_not_enable_real_trading": True,
        },
        "selected_at_5": selected_5,
        "selected_at_8": selected_8,
        "added_by_limit_8": added_by_8,
        "expected_added_symbols": [r["symbol"] for r in added_by_8],
        "rollback": {
            "RUNTIME_ACTIVE_UNIVERSE_LIMIT": "5",
            "RUNTIME_MAX_SYMBOLS": "5",
        },
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print("VERDICT=RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_READY")
    print("TEST_RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
