#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== GLOBAL_LINK_REPAIR_VALIDATION_V1 ===")
    print("mode=validation_read_only")
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
                WITH trades AS (
                    SELECT id::text AS trade_id, symbol, strategy, timeframe, entry_ts
                    FROM public.closed_trades
                    WHERE symbol IS NOT NULL
                      AND timeframe IS NOT NULL
                      AND entry_ts IS NOT NULL
                      AND net_pnl IS NOT NULL
                ),
                links AS (
                    SELECT trade_id, link_quality, link_reason
                    FROM research.trade_state_snapshots_v1
                )
                SELECT
                    COUNT(*) AS closed_trades,
                    SUM(CASE WHEN l.link_quality='EXACT_OR_NEAREST_OK' THEN 1 ELSE 0 END) AS linked,
                    SUM(CASE WHEN COALESCE(l.link_quality,'NO_LINK_ROW') <> 'EXACT_OR_NEAREST_OK' THEN 1 ELSE 0 END) AS not_linked,
                    SUM(CASE WHEN l.link_reason ILIKE 'global_link_repair_v1%' THEN 1 ELSE 0 END) AS repaired_links
                FROM trades t
                LEFT JOIN links l ON l.trade_id=t.trade_id;
            """)
            closed_trades, linked, not_linked, repaired_links = cur.fetchone()

            cur.execute("""
                WITH trades AS (
                    SELECT id::text AS trade_id, symbol, timeframe, entry_ts
                    FROM public.closed_trades
                    WHERE symbol IS NOT NULL
                      AND timeframe IS NOT NULL
                      AND entry_ts IS NOT NULL
                      AND net_pnl IS NOT NULL
                )
                SELECT
                    t.symbol,
                    t.timeframe,
                    COUNT(*) AS trades,
                    SUM(CASE WHEN l.link_quality='EXACT_OR_NEAREST_OK' THEN 1 ELSE 0 END) AS linked
                FROM trades t
                LEFT JOIN research.trade_state_snapshots_v1 l
                  ON l.trade_id=t.trade_id
                GROUP BY t.symbol, t.timeframe
                ORDER BY t.symbol, t.timeframe;
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT trade_id, COUNT(*)
                    FROM research.trade_state_snapshots_v1
                    GROUP BY trade_id
                    HAVING COUNT(*) > 1
                ) q;
            """)
            duplicates = cur.fetchone()[0]

    coverage = float(linked or 0) / float(closed_trades or 1)

    print("")
    print("SUMMARY")
    print(f"closed_trades={closed_trades}")
    print(f"linked={linked}")
    print(f"not_linked={not_linked}")
    print(f"repaired_links={repaired_links}")
    print(f"coverage={coverage:.4f}")
    print(f"duplicates={duplicates}")

    print("")
    print("INSTRUMENT_TIMEFRAME_COVERAGE")
    for symbol, timeframe, trades, linked_count in rows:
        pct = float(linked_count or 0) / float(trades or 1)
        print(
            "COVERAGE_ROW "
            f"symbol={symbol} "
            f"timeframe={timeframe} "
            f"trades={trades} "
            f"linked={linked_count} "
            f"coverage={pct:.4f}"
        )

    verdict = "GLOBAL_LINK_REPAIR_VALIDATION_OK"
    if duplicates:
        verdict = "GLOBAL_LINK_REPAIR_VALIDATION_DUPLICATES"
    elif coverage < 0.90:
        verdict = "GLOBAL_LINK_REPAIR_VALIDATION_COVERAGE_BELOW_THRESHOLD"
    elif not_linked:
        verdict = "GLOBAL_LINK_REPAIR_VALIDATION_PARTIAL_REMAINING"

    print("")
    print(f"VERDICT={verdict}")
    return 0 if verdict == "GLOBAL_LINK_REPAIR_VALIDATION_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
