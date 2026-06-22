#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2

print("=== EQUITY_SIGNAL_GENERATION_AUDIT_V1 ===")
print("mode=read_only_audit")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("telegram_send=0")

dsn = os.getenv("DATABASE_URL")
if not dsn:
    print("VERDICT=DATABASE_URL_NOT_SET")
    sys.exit(1)

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            select column_name
            from information_schema.columns
            where table_schema='public'
              and table_name='runtime_guard_pre_signal_block_audit_v1'
        """)
        guard_cols = {r[0] for r in cur.fetchall()}
        has_guard = bool(guard_cols)

        print(f"HAS_GUARD_TABLE={int(has_guard)}")
        print("GUARD_COLUMNS=" + ",".join(sorted(guard_cols)))

        cur.execute("""
            with universe as (
                select symbol, strategy, timeframe, is_enabled
                from runtime_active_universe
                where symbol like '%@MISX'
            ),
            bars as (
                select
                    symbol,
                    count(*) filter (where timeframe='M1')::int as m1_bars,
                    count(*) filter (where timeframe='M5')::int as m5_bars,
                    max(ts) as last_bar_ts
                from market_bars
                where symbol like '%@MISX'
                group by symbol
            ),
            sig as (
                select symbol, count(*)::int as signals_total, max(created_at) as last_signal_ts
                from signals
                where symbol like '%@MISX'
                group by symbol
            )
            select
                u.symbol,
                u.strategy,
                u.timeframe,
                u.is_enabled,
                coalesce(b.m1_bars, 0),
                coalesce(b.m5_bars, 0),
                b.last_bar_ts,
                coalesce(s.signals_total, 0),
                s.last_signal_ts
            from universe u
            left join bars b on b.symbol = u.symbol
            left join sig s on s.symbol = u.symbol
            order by u.symbol
        """)

        rows = cur.fetchall()

        equities = 0
        with_bars = 0
        with_signals = 0

        for row in rows:
            symbol, strategy, timeframe, enabled, m1, m5, last_bar_ts, signals, last_signal_ts = row
            equities += 1
            if last_bar_ts:
                with_bars += 1
            if signals:
                with_signals += 1

            status = "NO_BARS"
            if last_bar_ts and not signals:
                status = "BARS_OK_SIGNALS_ZERO"
            elif signals:
                status = "SIGNALS_PRESENT"

            print(
                "EQUITY_SIGNAL_FLOW_ROW "
                f"symbol={symbol} "
                f"strategy={strategy} "
                f"timeframe={timeframe} "
                f"enabled={enabled} "
                f"m1_bars={m1} "
                f"m5_bars={m5} "
                f"last_bar_ts={last_bar_ts} "
                f"signals={signals} "
                f"last_signal_ts={last_signal_ts} "
                f"status={status}"
            )

        if has_guard:
            cur.execute("""
                select
                    symbol,
                    strategy,
                    timeframe,
                    block_reason,
                    count(*)::int as rows_total,
                    max(created_at) as last_seen
                from runtime_guard_pre_signal_block_audit_v1
                where symbol like '%@MISX'
                group by symbol, strategy, timeframe, block_reason
                order by rows_total desc, symbol
                limit 50
            """)

            for row in cur.fetchall():
                symbol, strategy, timeframe, reason, rows_total, last_seen = row
                print(
                    "EQUITY_GUARD_ROW "
                    f"symbol={symbol} "
                    f"strategy={strategy} "
                    f"timeframe={timeframe} "
                    f"block_reason={reason} "
                    f"rows={rows_total} "
                    f"last_seen={last_seen}"
                )

        if equities == 0:
            decision = "NO_EQUITIES_IN_RUNTIME"
        elif with_bars == 0:
            decision = "EQUITY_NO_BARS"
        elif with_signals == 0 and has_guard:
            decision = "EQUITY_BLOCKED_BEFORE_SIGNAL"
        elif with_signals == 0:
            decision = "EQUITY_SIGNAL_EMIT_NOT_REACHED"
        else:
            decision = "EQUITY_SIGNALS_PRESENT"

        print(
            "EQUITY_SIGNAL_GENERATION_SUMMARY "
            f"runtime_equities={equities} "
            f"with_bars={with_bars} "
            f"with_signals={with_signals} "
            f"has_guard_table={int(has_guard)} "
            f"decision={decision}"
        )

print("VERDICT=EQUITY_SIGNAL_GENERATION_AUDIT_READY")
print("TEST_EQUITY_SIGNAL_GENERATION_AUDIT_V1_OK")
