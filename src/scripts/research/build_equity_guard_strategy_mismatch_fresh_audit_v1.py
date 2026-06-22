#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2

WINDOW_HOURS = 6

print("=== EQUITY_GUARD_STRATEGY_MISMATCH_FRESH_AUDIT_V1 ===")
print("mode=read_only_audit")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print(f"window_hours={WINDOW_HOURS}")

dsn = os.getenv("DATABASE_URL")
if not dsn:
    print("VERDICT=DATABASE_URL_NOT_SET")
    sys.exit(1)

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            with runtime as (
                select symbol, strategy as runtime_strategy, timeframe, is_enabled
                from runtime_active_universe
                where symbol like '%%@MISX'
            ),
            guard_fresh as (
                select symbol, strategy as guard_strategy, timeframe, block_reason, created_at
                from runtime_guard_pre_signal_block_audit_v1
                where symbol like '%%@MISX'
                  and created_at >= now() - interval '6 hours'
            )
            select
                g.symbol,
                r.runtime_strategy,
                g.guard_strategy,
                g.timeframe,
                g.block_reason,
                count(*)::int as rows_total,
                max(g.created_at) as last_seen
            from guard_fresh g
            left join runtime r on r.symbol = g.symbol
            group by g.symbol, r.runtime_strategy, g.guard_strategy, g.timeframe, g.block_reason
            order by rows_total desc, g.symbol
        """)

        rows = cur.fetchall()

        total = 0
        mismatch = 0
        fresh_volatility_rows = 0
        fresh_legacy_rows = 0

        for row in rows:
            symbol, runtime_strategy, guard_strategy, timeframe, block_reason, rows_total, last_seen = row
            total += rows_total

            status = "MATCH"
            if runtime_strategy and runtime_strategy != guard_strategy:
                status = "MISMATCH"
                mismatch += rows_total

            if guard_strategy == "VOLATILITY_BREAKOUT_EQUITY":
                fresh_volatility_rows += rows_total
            elif guard_strategy in ("MEAN_REVERSION_EQUITY", "TREND_PULLBACK_EQUITY"):
                fresh_legacy_rows += rows_total

            print(
                "FRESH_GUARD_ROW "
                f"symbol={symbol} "
                f"runtime_strategy={runtime_strategy} "
                f"guard_strategy={guard_strategy} "
                f"timeframe={timeframe} "
                f"block_reason={block_reason} "
                f"rows={rows_total} "
                f"last_seen={last_seen} "
                f"status={status}"
            )

        print(
            "FRESH_SUMMARY "
            f"fresh_rows={total} "
            f"fresh_mismatch_rows={mismatch} "
            f"fresh_volatility_rows={fresh_volatility_rows} "
            f"fresh_legacy_rows={fresh_legacy_rows}"
        )

        if total == 0:
            verdict = "FRESH_GUARD_NO_ROWS"
        elif fresh_legacy_rows > fresh_volatility_rows:
            verdict = "FRESH_STRATEGY_MISMATCH_CONFIRMED"
        elif mismatch > 0:
            verdict = "FRESH_MIXED_STRATEGY_REVIEW"
        else:
            verdict = "FRESH_STRATEGY_MATCH_OK"

        print(f"VERDICT={verdict}")

print("TEST_EQUITY_GUARD_STRATEGY_MISMATCH_FRESH_AUDIT_V1_OK")
