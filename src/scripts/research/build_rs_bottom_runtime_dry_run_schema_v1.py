#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg

TABLE = "analytics_rs_bottom_runtime_dry_run_v1"

DDL = f"""
create table if not exists {TABLE} (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    strategy text not null default 'RS_BOTTOM_RUNTIME_DRY_RUN_V1',
    mode text not null default 'SHADOW',

    symbol text not null,
    family text not null,
    signal_ts timestamptz not null,
    session_msk int,

    selection text not null default 'BOTTOM3',
    filter_name text not null default 'COMPRESSION_RANGE',

    entry_price numeric,
    horizon_min int not null,
    future_ts timestamptz,
    future_price numeric,
    return_pct numeric,

    status text not null default 'WAITING',

    runtime_allow_trading boolean not null default false,
    execution_enabled boolean not null default false,
    real_trading_enabled boolean not null default false,
    paper_orders boolean not null default false,

    source_table text not null default 'analytics_futures_rs_bottom_paper_observation_v1',
    source_id bigint,
    payload jsonb not null default '{{}}'::jsonb
);
"""

INDEXES = [
    f"create index if not exists idx_{TABLE}_symbol_ts on {TABLE}(symbol, signal_ts desc)",
    f"create index if not exists idx_{TABLE}_status on {TABLE}(status)",
    f"create index if not exists idx_{TABLE}_family on {TABLE}(family)",
    f"create unique index if not exists uq_{TABLE}_signal_horizon on {TABLE}(symbol, signal_ts, horizon_min, selection, filter_name)",
]

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_RUNTIME_DRY_RUN_SCHEMA_V1 ===")
    print("mode=schema_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("paper_orders=0")
    print(f"target_table={TABLE}")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            for stmt in INDEXES:
                cur.execute(stmt)
            conn.commit()

            cur.execute("""
                select column_name
                from information_schema.columns
                where table_schema='public'
                  and table_name=%s
                order by ordinal_position
            """, (TABLE,))
            cols = [r[0] for r in cur.fetchall()]

    required = {
        "symbol", "family", "signal_ts", "entry_price", "horizon_min",
        "future_ts", "future_price", "return_pct", "status", "session_msk",
        "runtime_allow_trading", "execution_enabled", "real_trading_enabled",
        "paper_orders"
    }

    missing = sorted(required - set(cols))

    print("SCHEMA_COLUMNS")
    for c in cols:
        print(f"COLUMN={c}")

    print("\nSCHEMA_SUMMARY")
    print(f"columns_total={len(cols)}")
    print(f"missing_required={len(missing)}")
    if missing:
        print("missing=" + ",".join(missing))
        print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_SCHEMA_INVALID")
        return 1

    print("VERDICT=RS_BOTTOM_RUNTIME_DRY_RUN_SCHEMA_READY")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
