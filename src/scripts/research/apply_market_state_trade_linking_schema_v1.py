#!/usr/bin/env python3

import os
import sys

import psycopg2


DDL = [
"""
CREATE TABLE IF NOT EXISTS research.trade_state_snapshots_v1 (
    trade_state_id BIGSERIAL PRIMARY KEY,

    trade_id TEXT NOT NULL,

    symbol TEXT NOT NULL,

    timeframe TEXT,

    entry_ts TIMESTAMPTZ,

    exit_ts TIMESTAMPTZ,

    entry_snapshot_id BIGINT
        REFERENCES research.market_state_snapshots_v1(snapshot_id),

    exit_snapshot_id BIGINT
        REFERENCES research.market_state_snapshots_v1(snapshot_id),

    entry_compact_signature TEXT,

    exit_compact_signature TEXT,

    holding_snapshot_count BIGINT,

    link_quality TEXT NOT NULL,

    link_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(trade_id)
);
""",

"""
CREATE INDEX IF NOT EXISTS idx_trade_state_trade_id
ON research.trade_state_snapshots_v1(trade_id);
""",

"""
CREATE INDEX IF NOT EXISTS idx_trade_state_symbol_entry
ON research.trade_state_snapshots_v1(symbol, entry_ts);
""",

"""
CREATE INDEX IF NOT EXISTS idx_trade_state_entry_signature
ON research.trade_state_snapshots_v1(entry_compact_signature);
""",

"""
CREATE INDEX IF NOT EXISTS idx_trade_state_exit_signature
ON research.trade_state_snapshots_v1(exit_compact_signature);
"""
]


def main():

    print("=== MARKET_STATE_TRADE_LINKING_SCHEMA_APPLY_V1 ===")
    print("mode=schema_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    if "--apply" not in sys.argv:
        print("db_update=0")
        print("VERDICT=REQUIRES_APPLY_FLAG")
        return 2

    db = os.environ.get("DATABASE_URL","")

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
    print("tables_applied=1")
    print("indexes_applied=4")
    print("schema=research")

    print("VERDICT=MARKET_STATE_TRADE_LINKING_SCHEMA_APPLY_OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
