#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DDL = """
CREATE TABLE IF NOT EXISTS plzl_shadow_accumulation_v1 (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_ts TIMESTAMPTZ,
    side TEXT NOT NULL,
    entry_price NUMERIC,
    stop_price NUMERIC,
    take_price NUMERIC,
    reason TEXT NOT NULL DEFAULT '',
    shadow_only BOOLEAN NOT NULL DEFAULT true,
    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
    execution_enabled BOOLEAN NOT NULL DEFAULT false,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_plzl_shadow_accumulation_symbol_ts
ON plzl_shadow_accumulation_v1(symbol, created_at DESC);
"""

def main() -> int:
    print("=== PLZL SHADOW ACCUMULATION V1 ===")
    print("mode=shadow_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()

    print("PLZL_SHADOW_ACCUMULATION_TABLE_READY")
    print("PLZL_SHADOW_ACCUMULATION_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
