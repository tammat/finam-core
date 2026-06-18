#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import psycopg2
from psycopg2.extras import RealDictCursor


CREATE_SQL = """
create table if not exists signal_strategy_discovery_events (
    id bigserial primary key,
    created_at timestamptz not null default now(),
    symbol text not null,
    reason text not null,
    source text not null,
    payload jsonb not null default '{}'::jsonb,
    status text not null default 'NEW',
    analyst_comment text not null default '',
    proposed_strategy text,
    proposed_timeframe text,
    proposed_continuous_symbol text
);

create index if not exists idx_signal_strategy_discovery_events_status
on signal_strategy_discovery_events(status);

create index if not exists idx_signal_strategy_discovery_events_symbol_created
on signal_strategy_discovery_events(symbol, created_at desc);
"""


CHECK_SQL = """
select exists (
    select 1
    from information_schema.tables
    where table_schema = 'public'
      and table_name = 'signal_strategy_discovery_events'
) as table_exists;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== SIGNAL STRATEGY DISCOVERY EVENTS V1 ===")
    print(f"mode={'apply' if args.apply else 'dry_run'}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(CHECK_SQL)
            before = cur.fetchone()["table_exists"]
            print(f"table_exists_before={int(before)}")

            if args.apply:
                cur.execute(CREATE_SQL)
                conn.commit()
            else:
                conn.rollback()

            cur.execute(CHECK_SQL)
            after = cur.fetchone()["table_exists"]
            print(f"table_exists_after={int(after)}")

    if args.apply:
        print("VERDICT=SIGNAL_STRATEGY_DISCOVERY_EVENTS_APPLIED")
    else:
        print("VERDICT=SIGNAL_STRATEGY_DISCOVERY_EVENTS_DRY_RUN_READY")

    print("SIGNAL_STRATEGY_DISCOVERY_EVENTS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
