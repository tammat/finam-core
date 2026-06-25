#!/usr/bin/env python3

import os
import psycopg2


SOURCE = "universe_backfill_v1"

TARGET_SYMBOLS = ("NGN6@RTSX", "BRN6@RTSX")


def fetch_one(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()


def main() -> int:
    print("=== GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_V1 ===")
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

    diagnostics = []

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ct.id::text,
                    ct.symbol,
                    ct.strategy,
                    ct.timeframe,
                    ct.entry_ts,
                    ct.exit_ts,
                    COALESCE(tss.link_quality, 'NO_LINK_ROW') AS link_quality,
                    tss.link_reason
                FROM public.closed_trades ct
                LEFT JOIN research.trade_state_snapshots_v1 tss
                  ON tss.trade_id = ct.id::text
                WHERE ct.symbol IN %s
                  AND ct.entry_ts IS NOT NULL
                  AND ct.net_pnl IS NOT NULL
                  AND COALESCE(tss.link_quality, 'NO_LINK_ROW') <> 'EXACT_OR_NEAREST_OK'
                ORDER BY ct.symbol, ct.timeframe, ct.entry_ts
                LIMIT 300;
                """,
                (TARGET_SYMBOLS,),
            )
            trades = cur.fetchall()

            print("")
            print("TRADE_DIAGNOSTIC_ROWS")

            for trade_id, symbol, strategy, timeframe, entry_ts, exit_ts, link_quality, link_reason in trades:
                exact_source = fetch_one(
                    cur,
                    """
                    SELECT COUNT(*), MIN(snapshot_ts), MAX(snapshot_ts)
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND source=%s;
                    """,
                    (symbol, timeframe, SOURCE),
                )

                any_source_same_tf = fetch_one(
                    cur,
                    """
                    SELECT COUNT(*), MIN(snapshot_ts), MAX(snapshot_ts)
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s
                      AND timeframe=%s;
                    """,
                    (symbol, timeframe),
                )

                same_symbol_any_tf = fetch_one(
                    cur,
                    """
                    SELECT COUNT(*), MIN(snapshot_ts), MAX(snapshot_ts)
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s;
                    """,
                    (symbol,),
                )

                nearest_prior = fetch_one(
                    cur,
                    """
                    SELECT snapshot_id, snapshot_ts, source, compact_signature
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND source=%s
                      AND snapshot_ts<=%s
                    ORDER BY snapshot_ts DESC
                    LIMIT 1;
                    """,
                    (symbol, timeframe, SOURCE, entry_ts),
                )

                nearest_any_source_prior = fetch_one(
                    cur,
                    """
                    SELECT snapshot_id, snapshot_ts, source, compact_signature
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND snapshot_ts<=%s
                    ORDER BY snapshot_ts DESC
                    LIMIT 1;
                    """,
                    (symbol, timeframe, entry_ts),
                )

                nearest_any_tf_prior = fetch_one(
                    cur,
                    """
                    SELECT snapshot_id, snapshot_ts, timeframe, source, compact_signature
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s
                      AND snapshot_ts<=%s
                    ORDER BY snapshot_ts DESC
                    LIMIT 1;
                    """,
                    (symbol, entry_ts),
                )

                exact_rows, exact_first, exact_last = exact_source
                any_tf_rows, any_tf_first, any_tf_last = same_symbol_any_tf
                same_tf_rows, same_tf_first, same_tf_last = any_source_same_tf

                if exact_rows == 0 and same_tf_rows > 0:
                    root = "SOURCE_FILTER_MISMATCH"
                    repair = "LINK_ALLOW_ALL_RESEARCH_SOURCES_OR_CORRECT_SOURCE"
                elif exact_rows == 0 and any_tf_rows > 0:
                    root = "TIMEFRAME_MISMATCH"
                    repair = "MAP_LIVE_TO_AVAILABLE_TIMEFRAME_OR_BACKFILL_LIVE"
                elif exact_rows == 0:
                    root = "NO_MARKET_STATE_FOR_SYMBOL_TIMEFRAME_SOURCE"
                    repair = "BACKFILL_MARKET_STATE_FOR_SYMBOL_TIMEFRAME_SOURCE"
                elif nearest_prior is None and exact_first is not None and entry_ts < exact_first:
                    root = "TRADE_BEFORE_FIRST_SNAPSHOT"
                    repair = "EXTEND_HISTORY_BACKWARD"
                elif nearest_prior is None:
                    root = "NO_PRIOR_SNAPSHOT"
                    repair = "CHECK_TS_ALIGNMENT_OR_EXTEND_HISTORY"
                else:
                    root = "LINKER_SQL_OR_CONFLICT_STATE_STALE"
                    repair = "RERUN_LINKING_WITH_DIAGNOSTIC_QUERY"

                diagnostics.append(root)

                print(
                    "DIAG_ROW "
                    f"trade_id={trade_id} "
                    f"symbol={symbol} "
                    f"strategy={strategy or 'UNKNOWN'} "
                    f"timeframe={timeframe} "
                    f"entry_ts={entry_ts} "
                    f"link_quality={link_quality} "
                    f"link_reason={link_reason or 'NONE'} "
                    f"exact_source_rows={exact_rows} "
                    f"exact_source_first={exact_first} "
                    f"exact_source_last={exact_last} "
                    f"same_tf_any_source_rows={same_tf_rows} "
                    f"same_symbol_any_tf_rows={any_tf_rows} "
                    f"nearest_prior_exists={int(nearest_prior is not None)} "
                    f"nearest_any_source_prior_exists={int(nearest_any_source_prior is not None)} "
                    f"nearest_any_tf_prior_exists={int(nearest_any_tf_prior is not None)} "
                    f"diagnostic_root={root} "
                    f"repair_action={repair}"
                )

            print("")
            print("SOURCE_DISTRIBUTION")
            cur.execute(
                """
                SELECT symbol, timeframe, source, COUNT(*), MIN(snapshot_ts), MAX(snapshot_ts)
                FROM research.market_state_snapshots_v1
                WHERE symbol IN %s
                GROUP BY symbol, timeframe, source
                ORDER BY symbol, timeframe, source;
                """,
                (TARGET_SYMBOLS,),
            )
            for symbol, timeframe, source, rows, first_ts, last_ts in cur.fetchall():
                print(
                    "SOURCE_ROW "
                    f"symbol={symbol} "
                    f"timeframe={timeframe} "
                    f"source={source} "
                    f"rows={rows} "
                    f"first_ts={first_ts} "
                    f"last_ts={last_ts}"
                )

    summary = {}
    for root in diagnostics:
        summary[root] = summary.get(root, 0) + 1

    print("")
    print("DIAGNOSTIC_SUMMARY")
    print(f"diagnosed_trades={len(diagnostics)}")
    for root, count in sorted(summary.items()):
        print(f"ROOT name={root} count={count}")

    verdict = "GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_READY"
    if not diagnostics:
        verdict = "GLOBAL_LINK_REPAIR_LINKER_DIAGNOSTIC_NO_LOST_TARGET_TRADES"

    print("")
    print("NEXT_STEPS")
    print("next=GLOBAL_LINK_REPAIR_IMPLEMENTATION_V1")

    print("")
    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
