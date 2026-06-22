#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2

print("=== EQUITIES_ACCUMULATION_MONITOR_V1 ===")
print("mode=read_only_monitor")
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
            with universe as (
                select
                    symbol,
                    strategy,
                    timeframe,
                    coalesce(is_enabled, true) as enabled
                from runtime_active_universe
                where symbol like '%%@MISX'
            ),
            bars as (
                select
                    symbol,
                    count(*) filter (where timeframe='M1')::int as m1_bars,
                    count(*) filter (where timeframe='M5')::int as m5_bars,
                    max(ts) as last_bar_ts
                from market_bars
                where symbol like '%%@MISX'
                group by symbol
            ),
            signal_rows as (
                select
                    symbol,
                    count(*)::int as signals_total
                from signals
                where symbol like '%%@MISX'
                group by symbol
            ),
            trade_rows as (
                select
                    symbol,
                    count(*)::int as trades_total
                from trades
                where symbol like '%%@MISX'
                group by symbol
            )
            select
                u.symbol,
                u.strategy,
                u.timeframe,
                u.enabled,
                coalesce(b.m1_bars, 0),
                coalesce(b.m5_bars, 0),
                b.last_bar_ts,
                coalesce(s.signals_total, 0),
                coalesce(t.trades_total, 0)
            from universe u
            left join bars b on b.symbol = u.symbol
            left join signal_rows s on s.symbol = u.symbol
            left join trade_rows t on t.symbol = u.symbol
            order by u.symbol
        """)

        rows = cur.fetchall()

        total = len(rows)
        with_bars = 0
        with_signals = 0
        with_trades = 0
        no_bars = 0

        for row in rows:
            symbol, strategy, timeframe, enabled, m1, m5, last_bar_ts, signals, trades = row

            if last_bar_ts:
                with_bars += 1
            else:
                no_bars += 1

            if signals > 0:
                with_signals += 1

            if trades > 0:
                with_trades += 1

            if not last_bar_ts:
                status = "NO_BARS"
            elif signals == 0:
                status = "BARS_OK_NO_SIGNALS"
            elif trades == 0:
                status = "SIGNALS_OK_NO_TRADES"
            else:
                status = "TRADES_PRESENT"

            print(
                "EQUITY_MONITOR_ROW "
                f"symbol={symbol} "
                f"strategy={strategy} "
                f"timeframe={timeframe} "
                f"enabled={enabled} "
                f"m1_bars={m1} "
                f"m5_bars={m5} "
                f"last_bar_ts={last_bar_ts} "
                f"signals={signals} "
                f"trades={trades} "
                f"status={status}"
            )

        if total == 0:
            decision = "NO_EQUITIES_IN_RUNTIME"
        elif no_bars > 0:
            decision = "EQUITY_BARS_REPAIR_REQUIRED"
        elif with_signals == 0:
            decision = "EQUITY_ACCUMULATION_WAIT_FOR_SIGNALS"
        elif with_trades == 0:
            decision = "EQUITY_SIGNALS_PRESENT_WAIT_FOR_TRADES"
        else:
            decision = "EQUITY_ACCUMULATION_ACTIVE"

        print(
            "EQUITY_MONITOR_SUMMARY "
            f"runtime_equities={total} "
            f"with_bars={with_bars} "
            f"no_bars={no_bars} "
            f"with_signals={with_signals} "
            f"with_trades={with_trades} "
            f"decision={decision}"
        )

print("VERDICT=EQUITIES_ACCUMULATION_MONITOR_READY")
print("TEST_EQUITIES_ACCUMULATION_MONITOR_V1_OK")
