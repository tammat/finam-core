#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2

print("=== EQUITIES_CLEAN_TRADE_SOURCE_AUDIT_V1 ===")
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
              and table_name='trades'
        """)
        cols = {r[0] for r in cur.fetchall()}

        print("TRADES_COLUMNS=" + ",".join(sorted(cols)))

        has_strategy = "strategy" in cols
        has_timeframe = "timeframe" in cols
        has_payload = "payload" in cols
        has_source = "source" in cols
        has_created_at = "created_at" in cols

        print(f"HAS_STRATEGY={int(has_strategy)}")
        print(f"HAS_TIMEFRAME={int(has_timeframe)}")
        print(f"HAS_PAYLOAD={int(has_payload)}")
        print(f"HAS_SOURCE={int(has_source)}")
        print(f"HAS_CREATED_AT={int(has_created_at)}")

        strategy_expr = "strategy" if has_strategy else "NULL::text"
        timeframe_expr = "timeframe" if has_timeframe else "NULL::text"
        source_expr = "source" if has_source else "NULL::text"
        created_expr = "created_at" if has_created_at else "NULL::timestamp"

        cur.execute(f"""
            select
                symbol,
                coalesce({strategy_expr}, 'UNKNOWN') as strategy,
                coalesce({timeframe_expr}, 'UNKNOWN') as timeframe,
                coalesce({source_expr}, 'UNKNOWN') as source,
                count(*)::int as trades,
                min({created_expr}) as first_trade,
                max({created_expr}) as last_trade
            from trades
            where symbol like '%%@MISX'
            group by symbol, strategy, timeframe, source
            order by symbol, trades desc
        """)

        total_trades = 0
        clean_runtime = 0
        legacy_or_unknown = 0

        for row in cur.fetchall():
            symbol, strategy, timeframe, source, trades, first_trade, last_trade = row
            total_trades += trades

            is_clean = (
                strategy == "VOLATILITY_BREAKOUT_EQUITY"
                and timeframe == "M5"
                and source not in ("PAPER_FILL_FALLBACK", "UNKNOWN", "LEGACY")
            )

            if is_clean:
                clean_runtime += trades
                classification = "CLEAN_RUNTIME_EQUITY"
            else:
                legacy_or_unknown += trades
                classification = "LEGACY_OR_FALLBACK_REVIEW"

            print(
                "EQUITY_TRADE_SOURCE_ROW "
                f"symbol={symbol} "
                f"strategy={strategy} "
                f"timeframe={timeframe} "
                f"source={source} "
                f"trades={trades} "
                f"first_trade={first_trade} "
                f"last_trade={last_trade} "
                f"classification={classification}"
            )

        print(
            "EQUITY_TRADE_SOURCE_SUMMARY "
            f"total_trades={total_trades} "
            f"clean_runtime={clean_runtime} "
            f"legacy_or_unknown={legacy_or_unknown}"
        )

        if total_trades > 0 and clean_runtime == 0:
            decision = "EQUITY_TRADES_NOT_CLEAN_RUNTIME"
        elif clean_runtime > 0:
            decision = "EQUITY_CLEAN_RUNTIME_TRADES_PRESENT"
        else:
            decision = "EQUITY_NO_TRADES"

        print(f"DECISION={decision}")

print("VERDICT=EQUITIES_CLEAN_TRADE_SOURCE_AUDIT_READY")
print("TEST_EQUITIES_CLEAN_TRADE_SOURCE_AUDIT_V1_OK")
