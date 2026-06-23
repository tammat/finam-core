#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import psycopg2

print("=== EQUITY_SIGNAL_GENERATION_AFTER_WIRING_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

dsn = os.getenv("DATABASE_URL")
if not dsn:
    raise SystemExit("DATABASE_URL_NOT_SET")

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:

        cur.execute("""
        select
            symbol,
            strategy,
            timeframe,
            is_enabled
        from runtime_active_universe
        where strategy='VOLATILITY_BREAKOUT_EQUITY'
        order by symbol
        """)

        runtime_rows = cur.fetchall()

        print("RUNTIME_ROWS")

        for row in runtime_rows:
            print(
                f"RUNTIME_ROW symbol={row[0]} "
                f"strategy={row[1]} "
                f"timeframe={row[2]} "
                f"enabled={row[3]}"
            )

        cur.execute("""
        select
            symbol,
            count(*)::int,
            max(created_at)
        from signals
        where symbol like '%@MISX'
        group by symbol
        order by count(*) desc
        """)

        signal_rows = cur.fetchall()

        print("SIGNAL_ROWS")

        total_signals = 0

        for symbol, cnt, ts in signal_rows:
            total_signals += cnt
            print(
                f"SIGNAL_ROW symbol={symbol} "
                f"count={cnt} "
                f"last_signal={ts}"
            )

        cur.execute("""
        select
            symbol,
            strategy,
            block_reason,
            count(*)::int,
            max(created_at)
        from runtime_guard_pre_signal_block_audit_v1
        where symbol like '%@MISX'
        group by symbol,strategy,block_reason
        order by count(*) desc
        limit 50
        """)

        guard_rows = cur.fetchall()

        print("GUARD_ROWS")

        for row in guard_rows:
            print(
                f"GUARD_ROW symbol={row[0]} "
                f"strategy={row[1]} "
                f"reason={row[2]} "
                f"count={row[3]} "
                f"last_seen={row[4]}"
            )

        print(
            f"SUMMARY runtime_symbols={len(runtime_rows)} "
            f"signals_total={total_signals} "
            f"guard_rows={len(guard_rows)}"
        )

        if total_signals == 0:
            verdict = "EQUITY_RUNTIME_OK_NO_SIGNALS"
        else:
            verdict = "EQUITY_SIGNALS_PRESENT"

        print(f"VERDICT={verdict}")

print("TEST_EQUITY_SIGNAL_GENERATION_AFTER_WIRING_V1_OK")
