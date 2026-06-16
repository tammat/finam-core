#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DDL = """
CREATE TABLE IF NOT EXISTS sber_d1_shadow_accumulation_v1 (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),

    symbol text NOT NULL,
    strategy text NOT NULL,
    timeframe text NOT NULL,

    signal_ts timestamptz NOT NULL,
    side text NOT NULL,

    entry_price numeric,
    stop_price numeric,
    take_price numeric,

    shadow_only boolean NOT NULL DEFAULT true,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,

    reason text,
    raw_json jsonb,

    UNIQUE(symbol, strategy, timeframe, signal_ts, side)
);

CREATE INDEX IF NOT EXISTS idx_sber_shadow_signal_ts
ON sber_d1_shadow_accumulation_v1(signal_ts DESC);
"""

def main() -> int:
    print("=== SBER D1 SHADOW ACCUMULATION V1 ===")
    print("mode=shadow_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()

    print("SBER_D1_SHADOW_ACCUMULATION_TABLE_READY")
    print("SBER_D1_SHADOW_ACCUMULATION_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
