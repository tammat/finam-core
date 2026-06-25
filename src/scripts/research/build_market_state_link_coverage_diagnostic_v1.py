#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_V1 ===")
    print("mode=diagnostic_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    MIN(entry_ts),
                    MAX(entry_ts),
                    COUNT(DISTINCT symbol),
                    COUNT(DISTINCT timeframe)
                FROM public.trade_outcomes
                WHERE symbol IS NOT NULL
                  AND entry_ts IS NOT NULL;
            """)
            trade_total, trade_first, trade_last, trade_symbols, trade_timeframes = cur.fetchone()

            cur.execute("""
                SELECT
                    COUNT(*),
                    MIN(snapshot_ts),
                    MAX(snapshot_ts),
                    COUNT(DISTINCT symbol),
                    COUNT(DISTINCT timeframe)
                FROM research.market_state_snapshots_v1;
            """)
            snap_total, snap_first, snap_last, snap_symbols, snap_timeframes = cur.fetchone()

            cur.execute("""
                SELECT
                    o.symbol,
                    COALESCE(o.timeframe, 'UNKNOWN') AS timeframe,
                    COUNT(*) AS trades,
                    MIN(o.entry_ts) AS first_trade,
                    MAX(o.entry_ts) AS last_trade,
                    COUNT(s.snapshot_id) AS matching_snapshots
                FROM public.trade_outcomes o
                LEFT JOIN research.market_state_snapshots_v1 s
                  ON s.symbol = o.symbol
                 AND s.timeframe = COALESCE(o.timeframe, 'UNKNOWN')
                 AND s.snapshot_ts <= o.entry_ts
                WHERE o.symbol IS NOT NULL
                  AND o.entry_ts IS NOT NULL
                GROUP BY o.symbol, COALESCE(o.timeframe, 'UNKNOWN')
                ORDER BY trades DESC, o.symbol, timeframe;
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT
                    tss.link_quality,
                    COUNT(*)
                FROM research.trade_state_snapshots_v1 tss
                GROUP BY tss.link_quality
                ORDER BY tss.link_quality;
            """)
            link_rows = cur.fetchall()

            cur.execute("""
                SELECT DISTINCT symbol, timeframe, MIN(snapshot_ts), MAX(snapshot_ts), COUNT(*)
                FROM research.market_state_snapshots_v1
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe;
            """)
            snapshot_ranges = cur.fetchall()

    print("")
    print("TRADE_OUTCOMES_RANGE")
    print(f"trade_total={trade_total}")
    print(f"trade_first={trade_first}")
    print(f"trade_last={trade_last}")
    print(f"trade_symbols={trade_symbols}")
    print(f"trade_timeframes={trade_timeframes}")

    print("")
    print("MARKET_STATE_SNAPSHOT_RANGE")
    print(f"snapshot_total={snap_total}")
    print(f"snapshot_first={snap_first}")
    print(f"snapshot_last={snap_last}")
    print(f"snapshot_symbols={snap_symbols}")
    print(f"snapshot_timeframes={snap_timeframes}")

    print("")
    print("LINK_QUALITY_CURRENT")
    for quality, count in link_rows:
        print(f"LINK_QUALITY quality={quality} count={count}")

    print("")
    print("TRADE_TO_SNAPSHOT_COVERAGE")
    for symbol, timeframe, trades, first_trade, last_trade, matching_snapshots in rows:
        print(
            "COVERAGE "
            f"symbol={symbol} "
            f"timeframe={timeframe} "
            f"trades={trades} "
            f"first_trade={first_trade} "
            f"last_trade={last_trade} "
            f"matching_prior_snapshots={matching_snapshots}"
        )

    print("")
    print("SNAPSHOT_RANGES")
    for symbol, timeframe, first_ts, last_ts, count in snapshot_ranges:
        print(
            "SNAPSHOT_RANGE "
            f"symbol={symbol} "
            f"timeframe={timeframe} "
            f"snapshots={count} "
            f"first_snapshot={first_ts} "
            f"last_snapshot={last_ts}"
        )

    print("")
    print("DIAGNOSIS")
    if not snap_total:
        print("root_cause=NO_MARKET_STATE_SNAPSHOTS")
    elif not trade_total:
        print("root_cause=NO_TRADE_OUTCOMES")
    else:
        print("root_cause=CHECK_TIME_SYMBOL_TIMEFRAME_COVERAGE")
        print("likely_cause=historical_trades_do_not_overlap_live_shadow_snapshots_or_timeframe_symbol_mismatch")

    print("")
    print("NEXT_STEPS")
    print("next=MARKET_STATE_LINK_COVERAGE_REPAIR_V1")

    print("")
    print("VERDICT=MARKET_STATE_LINK_COVERAGE_DIAGNOSTIC_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
