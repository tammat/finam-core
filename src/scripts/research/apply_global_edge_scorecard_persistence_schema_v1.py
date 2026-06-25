#!/usr/bin/env python3

import os
import sys
import psycopg2

DDL = [
"""
CREATE TABLE IF NOT EXISTS research.analytics_global_edge_scorecard_runs_v1 (
    run_id BIGSERIAL PRIMARY KEY,
    run_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_script TEXT NOT NULL,
    source_checkpoint TEXT,
    rows_total BIGINT NOT NULL DEFAULT 0,
    positive_rows BIGINT NOT NULL DEFAULT 0,
    research_candidates BIGINT NOT NULL DEFAULT 0,
    micro_live_candidates BIGINT NOT NULL DEFAULT 0,
    research_version TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"""
CREATE TABLE IF NOT EXISTS research.analytics_global_edge_scorecard_v1 (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES research.analytics_global_edge_scorecard_runs_v1(run_id),
    symbol TEXT,
    strategy TEXT,
    timeframe TEXT,
    instrument_signature TEXT,
    fx_signature TEXT,
    energy_signature TEXT,
    trades BIGINT NOT NULL DEFAULT 0,
    wins BIGINT NOT NULL DEFAULT 0,
    losses BIGINT NOT NULL DEFAULT 0,
    winrate NUMERIC,
    net_pnl NUMERIC,
    expectancy NUMERIC,
    profit_factor NUMERIC,
    first_trade TIMESTAMPTZ,
    last_trade TIMESTAMPTZ,
    status TEXT NOT NULL,
    reason TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
""",
"CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_run_v1 ON research.analytics_global_edge_scorecard_v1(run_id);",
"CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_status_v1 ON research.analytics_global_edge_scorecard_v1(status);",
"""
CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_signature_v1
ON research.analytics_global_edge_scorecard_v1(instrument_signature, fx_signature, energy_signature);
""",
"""
CREATE INDEX IF NOT EXISTS idx_global_edge_scorecard_symbol_strategy_v1
ON research.analytics_global_edge_scorecard_v1(symbol, strategy, timeframe);
""",
]

def main() -> int:
    print("=== GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_V1 ===")
    print("mode=schema_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    if "--apply" not in sys.argv:
        print("db_update=0")
        print("VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_REQUIRES_APPLY_FLAG")
        return 2

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            for sql in DDL:
                cur.execute(sql)
        conn.commit()

    print("db_update=1")
    print("tables_applied=2")
    print("indexes_applied=4")
    print("schema=research")
    print("VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_SCHEMA_APPLY_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
