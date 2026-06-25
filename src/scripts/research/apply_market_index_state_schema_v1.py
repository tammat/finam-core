#!/usr/bin/env python3

import os
import sys
import psycopg2

DDL = [

"""
CREATE TABLE IF NOT EXISTS research.market_index_state_context_v1 (

    context_id BIGSERIAL PRIMARY KEY,

    context_ts TIMESTAMPTZ NOT NULL,

    context_code TEXT NOT NULL,

    context_symbol TEXT NOT NULL,

    timeframe TEXT NOT NULL,

    trend_state TEXT,

    volatility_state TEXT,

    session_state TEXT,

    close NUMERIC,

    canonical_context_signature TEXT NOT NULL,

    compact_context_signature TEXT NOT NULL,

    source TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(
        context_ts,
        context_code,
        context_symbol,
        timeframe,
        compact_context_signature
    )
);
""",

"""
CREATE TABLE IF NOT EXISTS research.market_state_index_context_links_v1 (

    link_id BIGSERIAL PRIMARY KEY,

    trade_state_id BIGINT
        REFERENCES research.trade_state_snapshots_v1(trade_state_id),

    trade_id TEXT NOT NULL,

    entry_snapshot_id BIGINT
        REFERENCES research.market_state_snapshots_v1(snapshot_id),

    entry_compact_signature TEXT,

    context_id BIGINT
        REFERENCES research.market_index_state_context_v1(context_id),

    context_code TEXT NOT NULL,

    context_compact_signature TEXT,

    link_quality TEXT NOT NULL,

    link_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(trade_state_id, context_code)
);
""",

"""
CREATE INDEX IF NOT EXISTS
idx_market_index_state_context_lookup_v1
ON research.market_index_state_context_v1
(
    context_code,
    context_symbol,
    timeframe,
    context_ts
);
""",

"""
CREATE INDEX IF NOT EXISTS
idx_market_index_state_context_signature_v1
ON research.market_index_state_context_v1
(
    context_code,
    compact_context_signature
);
""",

"""
CREATE INDEX IF NOT EXISTS
idx_market_state_index_context_links_trade_v1
ON research.market_state_index_context_links_v1
(
    trade_id
);
""",

"""
CREATE INDEX IF NOT EXISTS
idx_market_state_index_context_links_context_v1
ON research.market_state_index_context_links_v1
(
    context_code,
    context_compact_signature
);
"""
]


def main():

    print("=== MARKET_INDEX_STATE_SCHEMA_APPLY_V1 ===")
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
    print("tables_applied=2")
    print("indexes_applied=4")
    print("schema=research")
    print("VERDICT=MARKET_INDEX_STATE_SCHEMA_APPLY_OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
