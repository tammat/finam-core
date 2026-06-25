#!/usr/bin/env python3

import os
import psycopg2


TARGETS = [
    "NGN6@RTSX",
    "BRN6@RTSX",
]

KEYWORDS = [
    "bar",
    "bars",
    "candle",
    "candles",
    "feature",
    "snapshot",
    "quote",
    "market",
]


def main() -> int:
    print("=== GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_V1 ===")
    print("mode=discovery_read_only")
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
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name;
            """)
            tables = cur.fetchall()

            print("")
            print("CANDIDATE_SOURCE_TABLES")

            usable_sources = 0

            for schema, table in tables:
                lower = table.lower()
                if not any(k in lower for k in KEYWORDS):
                    continue

                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema=%s
                      AND table_name=%s
                    ORDER BY ordinal_position;
                """, (schema, table))
                cols = [r[0] for r in cur.fetchall()]

                has_symbol = "symbol" in cols
                has_timeframe = "timeframe" in cols
                has_close = "close" in cols

                ts_col = None
                for candidate in ("ts", "bar_ts", "timestamp", "created_at"):
                    if candidate in cols:
                        ts_col = candidate
                        break

                verdict = "NOT_USABLE"
                target_rows = 0

                if has_symbol and ts_col:
                    for symbol in TARGETS:
                        try:
                            cur.execute(
                                f"""
                                SELECT COUNT(*)
                                FROM {schema}.{table}
                                WHERE symbol=%s;
                                """,
                                (symbol,),
                            )
                            target_rows += int(cur.fetchone()[0])
                        except Exception as exc:
                            conn.rollback()
                            print(
                                "SOURCE_ERROR "
                                f"name={schema}.{table} "
                                f"error={str(exc).replace(chr(10), ' ')}"
                            )
                            target_rows = 0
                            break

                if target_rows > 0 and has_symbol and has_timeframe and has_close and ts_col:
                    verdict = "USABLE_FEATURE_OR_BAR_SOURCE"
                    usable_sources += 1
                elif target_rows > 0 and has_symbol and ts_col:
                    verdict = "USABLE_NEEDS_MAPPING"

                print(
                    "SOURCE "
                    f"name={schema}.{table} "
                    f"has_symbol={int(has_symbol)} "
                    f"has_timeframe={int(has_timeframe)} "
                    f"has_close={int(has_close)} "
                    f"ts_col={ts_col or 'NONE'} "
                    f"target_rows={target_rows} "
                    f"verdict={verdict}"
                )

            print("")
            print("TARGET_COVERAGE")

            for symbol in TARGETS:
                cur.execute("""
                    SELECT
                        COUNT(*),
                        MIN(entry_ts),
                        MAX(entry_ts)
                    FROM public.closed_trades
                    WHERE symbol=%s;
                """, (symbol,))
                trades, first_trade, last_trade = cur.fetchone()

                cur.execute("""
                    SELECT
                        COUNT(*),
                        MIN(ts),
                        MAX(ts)
                    FROM public.feature_snapshots
                    WHERE symbol=%s;
                """, (symbol,))
                feature_rows, first_feature, last_feature = cur.fetchone()

                cur.execute("""
                    SELECT
                        COUNT(*),
                        MIN(snapshot_ts),
                        MAX(snapshot_ts)
                    FROM research.market_state_snapshots_v1
                    WHERE symbol=%s;
                """, (symbol,))
                state_rows, first_state, last_state = cur.fetchone()

                print(
                    "TARGET "
                    f"symbol={symbol} "
                    f"closed_trades={trades} "
                    f"first_trade={first_trade} "
                    f"last_trade={last_trade} "
                    f"feature_rows={feature_rows} "
                    f"first_feature={first_feature} "
                    f"last_feature={last_feature} "
                    f"market_state_rows={state_rows} "
                    f"first_state={first_state} "
                    f"last_state={last_state}"
                )

    print("")
    print("SUMMARY")
    print(f"targets={len(TARGETS)}")
    print(f"usable_sources={usable_sources}")

    verdict = "GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_SOURCE_FOUND"
    if usable_sources == 0:
        verdict = "GLOBAL_LINK_REPAIR_SOURCE_DISCOVERY_NO_SOURCE"

    print("")
    print("NEXT_STEPS")
    print("next=GLOBAL_LINK_REPAIR_IMPLEMENTATION_V1")
    print("next=GLOBAL_LINK_REPAIR_SOURCE_GAP_PLAN_V1")

    print("")
    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
