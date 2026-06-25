#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_V1 ===")
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

    target_symbol = "BRN6@RTSX"
    target_timeframe = "M5"
    window_start = "2026-05-18T00:00:00+00:00"
    window_end = "2026-05-27T23:59:59+00:00"

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND (
                      table_name ILIKE '%bar%'
                      OR table_name ILIKE '%candle%'
                      OR table_name ILIKE '%quote%'
                      OR table_name ILIKE '%feature%'
                  )
                ORDER BY table_schema, table_name;
            """)
            tables = cur.fetchall()

            print("")
            print("CANDIDATE_SOURCE_TABLES")

            source_rows = []

            for schema, table in tables:
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema=%s
                      AND table_name=%s
                    ORDER BY ordinal_position;
                """, (schema, table))
                cols = [r[0] for r in cur.fetchall()]
                print(f"TABLE name={schema}.{table} columns={','.join(cols)}")

                has_symbol = "symbol" in cols
                has_timeframe = "timeframe" in cols
                ts_col = None
                for candidate in ("ts", "bar_ts", "timestamp", "created_at"):
                    if candidate in cols:
                        ts_col = candidate
                        break

                if has_symbol and has_timeframe and ts_col:
                    sql = f"""
                        SELECT COUNT(*), MIN({ts_col}), MAX({ts_col})
                        FROM {schema}.{table}
                        WHERE symbol=%s
                          AND timeframe=%s
                          AND {ts_col} >= %s
                          AND {ts_col} <= %s;
                    """
                    try:
                        cur.execute(sql, (target_symbol, target_timeframe, window_start, window_end))
                        count, first_ts, last_ts = cur.fetchone()
                        source_rows.append((schema, table, ts_col, count, first_ts, last_ts))
                    except Exception as exc:
                        conn.rollback()
                        source_rows.append((schema, table, ts_col, "ERROR", None, str(exc).replace("\n", " ")))

            print("")
            print("SOURCE_COVERAGE")
            for schema, table, ts_col, count, first_ts, last_ts in source_rows:
                print(
                    "SOURCE "
                    f"name={schema}.{table} "
                    f"ts_col={ts_col} "
                    f"rows={count} "
                    f"first={first_ts} "
                    f"last={last_ts}"
                )

    usable = [r for r in source_rows if isinstance(r[3], int) and r[3] > 0]

    print("")
    print("SUMMARY")
    print(f"target_symbol={target_symbol}")
    print(f"target_timeframe={target_timeframe}")
    print(f"window_start={window_start}")
    print(f"window_end={window_end}")
    print(f"candidate_tables={len(tables)}")
    print(f"usable_sources={len(usable)}")

    if usable:
        best = sorted(usable, key=lambda r: r[3], reverse=True)[0]
        print(f"best_source={best[0]}.{best[1]}")
        print(f"best_ts_col={best[2]}")
        print(f"best_rows={best[3]}")
        verdict = "MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_SOURCE_FOUND"
    else:
        print("best_source=NONE")
        verdict = "MARKET_STATE_BACKFILL_SOURCE_DIAGNOSTIC_NO_SOURCE"

    print("")
    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
