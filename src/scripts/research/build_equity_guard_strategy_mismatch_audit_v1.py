#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2

print("=== EQUITY_GUARD_STRATEGY_MISMATCH_AUDIT_V1 ===")
print("mode=read_only_audit")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")

dsn = os.getenv("DATABASE_URL")

if not dsn:
    print("VERDICT=DATABASE_URL_NOT_SET")
    sys.exit(1)

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:

        cur.execute("""
            select
                symbol,
                strategy,
                timeframe,
                is_enabled
            from runtime_active_universe
            where symbol like '%@MISX'
            order by symbol
        """)

        runtime_rows = cur.fetchall()

        runtime_map = {}

        for row in runtime_rows:
            symbol, strategy, timeframe, enabled = row

            runtime_map[symbol] = strategy

            print(
                "RUNTIME_ROW "
                f"symbol={symbol} "
                f"strategy={strategy} "
                f"timeframe={timeframe} "
                f"enabled={enabled}"
            )

        cur.execute("""
            select
                symbol,
                strategy,
                count(*)::int as rows_total
            from runtime_guard_pre_signal_block_audit_v1
            where symbol like '%@MISX'
            group by symbol, strategy
            order by rows_total desc
        """)

        mismatch = 0

        for row in cur.fetchall():
            symbol, guard_strategy, rows_total = row

            runtime_strategy = runtime_map.get(symbol)

            status = "MATCH"

            if runtime_strategy and runtime_strategy != guard_strategy:
                mismatch += 1
                status = "MISMATCH"

            print(
                "GUARD_ROW "
                f"symbol={symbol} "
                f"runtime_strategy={runtime_strategy} "
                f"guard_strategy={guard_strategy} "
                f"rows={rows_total} "
                f"status={status}"
            )

        print(
            f"SUMMARY mismatch={mismatch}"
        )

        if mismatch > 0:
            verdict = "STRATEGY_MISMATCH_CONFIRMED"
        else:
            verdict = "STRATEGY_MATCH"

        print(f"VERDICT={verdict}")

print("TEST_EQUITY_GUARD_STRATEGY_MISMATCH_AUDIT_V1_OK")
