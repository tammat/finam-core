#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_V1 ===")
    print("mode=coverage_read_only")
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
                WITH trade_windows AS (
                    SELECT
                        symbol,
                        timeframe,
                        COUNT(*) AS trades,
                        MIN(entry_ts) AS first_entry,
                        MAX(entry_ts) AS last_entry
                    FROM public.closed_trades
                    WHERE symbol IS NOT NULL
                      AND timeframe IS NOT NULL
                      AND entry_ts IS NOT NULL
                    GROUP BY symbol, timeframe
                ),
                feature_coverage AS (
                    SELECT
                        fs.symbol,
                        fs.timeframe,
                        COUNT(*) AS feature_rows,
                        MIN(fs.ts) AS first_feature,
                        MAX(fs.ts) AS last_feature
                    FROM public.feature_snapshots fs
                    GROUP BY fs.symbol, fs.timeframe
                )
                SELECT
                    tw.symbol,
                    tw.timeframe,
                    tw.trades,
                    tw.first_entry,
                    tw.last_entry,
                    COALESCE(fc.feature_rows, 0) AS feature_rows,
                    fc.first_feature,
                    fc.last_feature,
                    CASE
                        WHEN fc.feature_rows IS NULL THEN 'NO_FEATURES'
                        WHEN fc.first_feature <= tw.first_entry
                         AND fc.last_feature >= tw.last_entry THEN 'FULL_COVERAGE'
                        WHEN fc.last_feature < tw.first_entry THEN 'FEATURES_BEFORE_TRADES'
                        WHEN fc.first_feature > tw.last_entry THEN 'FEATURES_AFTER_TRADES'
                        ELSE 'PARTIAL_COVERAGE'
                    END AS coverage_status
                FROM trade_windows tw
                LEFT JOIN feature_coverage fc
                  ON fc.symbol = tw.symbol
                 AND fc.timeframe = tw.timeframe
                ORDER BY tw.trades DESC, tw.symbol, tw.timeframe;
            """)
            rows = cur.fetchall()

    print("")
    print("SOURCE_COVERAGE_ROWS")

    full = 0
    partial = 0
    none = 0
    total_trades = 0
    covered_trades = 0

    for row in rows:
        symbol, timeframe, trades, first_entry, last_entry, feature_rows, first_feature, last_feature, status = row

        total_trades += int(trades)
        if status == "FULL_COVERAGE":
            full += 1
            covered_trades += int(trades)
        elif status == "PARTIAL_COVERAGE":
            partial += 1
        else:
            none += 1

        print(
            "COVERAGE_ROW "
            f"symbol={symbol} "
            f"timeframe={timeframe} "
            f"trades={trades} "
            f"first_entry={first_entry} "
            f"last_entry={last_entry} "
            f"feature_rows={feature_rows} "
            f"first_feature={first_feature} "
            f"last_feature={last_feature} "
            f"status={status}"
        )

    print("")
    print("SUMMARY")
    print(f"windows_total={len(rows)}")
    print(f"full_coverage_windows={full}")
    print(f"partial_coverage_windows={partial}")
    print(f"no_coverage_windows={none}")
    print(f"closed_trades_total={total_trades}")
    print(f"closed_trades_full_coverage={covered_trades}")

    verdict = "HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_READY"
    if full == 0:
        verdict = "HISTORICAL_MARKET_STATE_BACKFILL_SOURCE_COVERAGE_NO_FULL_WINDOWS"

    print("")
    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
