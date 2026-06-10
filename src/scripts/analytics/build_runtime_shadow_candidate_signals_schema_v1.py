#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

SQL = """
CREATE TABLE IF NOT EXISTS runtime_shadow_candidate_signals_v1 (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    root TEXT NOT NULL,
    strategy TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    signal_ts TIMESTAMPTZ NOT NULL,
    side TEXT NOT NULL,
    entry_price DOUBLE PRECISION,
    qty DOUBLE PRECISION,

    shadow_only INTEGER NOT NULL DEFAULT 1,
    runtime_allow INTEGER NOT NULL DEFAULT 0,
    execution_enabled INTEGER NOT NULL DEFAULT 0,

    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    UNIQUE(symbol, strategy, timeframe, signal_ts, side)
);

CREATE INDEX IF NOT EXISTS idx_runtime_shadow_candidate_signals_v1_symbol_ts
ON runtime_shadow_candidate_signals_v1(symbol, signal_ts DESC);

CREATE INDEX IF NOT EXISTS idx_runtime_shadow_candidate_signals_v1_strategy_ts
ON runtime_shadow_candidate_signals_v1(strategy, signal_ts DESC);

CREATE INDEX IF NOT EXISTS idx_runtime_shadow_candidate_signals_v1_runtime_guard
ON runtime_shadow_candidate_signals_v1(runtime_allow, execution_enabled);
"""

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME SHADOW CANDIDATE SIGNALS SCHEMA V1 ===")
    print("mode=schema_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("table=runtime_shadow_candidate_signals_v1")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)

    print("SCHEMA_ROW table=runtime_shadow_candidate_signals_v1 status=created_or_exists")
    print("GUARD_ROW shadow_only_default=1 runtime_allow_default=0 execution_enabled_default=0")
    print("VERDICT=RUNTIME_SHADOW_CANDIDATE_SIGNALS_SCHEMA_READY")
    print("RUNTIME_SHADOW_CANDIDATE_SIGNALS_SCHEMA_V1_OK")

if __name__ == "__main__":
    main()
