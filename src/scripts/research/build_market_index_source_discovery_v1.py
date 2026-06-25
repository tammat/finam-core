#!/usr/bin/env python3

import os
import psycopg2


KEYWORDS = [
    "index",
    "imoex",
    "rtsi",
    "moex",
    "usd",
    "rub",
    "brent",
    "market",
    "bar",
    "feature",
]


def main() -> int:
    print("=== MARKET_INDEX_SOURCE_DISCOVERY_V1 ===")
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
            print("INDEX_SOURCE_CANDIDATES")

            candidates = 0

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

                has_symbol = int("symbol" in cols)
                has_timeframe = int("timeframe" in cols)
                has_close = int("close" in cols)
                has_ts = int(any(c in cols for c in ("ts", "bar_ts", "timestamp", "created_at")))
                has_feature_state = int(any(c in cols for c in ("trend_state", "volatility_state", "session_state")))

                ts_col = "NONE"
                for c in ("ts", "bar_ts", "timestamp", "created_at"):
                    if c in cols:
                        ts_col = c
                        break

                rows = 0
                first_ts = None
                last_ts = None

                try:
                    cur.execute(f"SELECT COUNT(*) FROM {schema}.{table};")
                    rows = cur.fetchone()[0]

                    if ts_col != "NONE":
                        cur.execute(f"SELECT MIN({ts_col}), MAX({ts_col}) FROM {schema}.{table};")
                        first_ts, last_ts = cur.fetchone()
                except Exception as exc:
                    conn.rollback()
                    print(f"SOURCE name={schema}.{table} error={str(exc).replace(chr(10), ' ')}")
                    continue

                verdict = "NOT_USABLE"
                if rows > 0 and has_symbol and has_timeframe and has_close and has_ts:
                    verdict = "USABLE_PRICE_SOURCE"
                    candidates += 1
                if rows > 0 and has_symbol and has_timeframe and has_close and has_ts and has_feature_state:
                    verdict = "USABLE_FEATURE_STATE_SOURCE"
                    candidates += 1

                print(
                    "SOURCE "
                    f"name={schema}.{table} "
                    f"rows={rows} "
                    f"has_symbol={has_symbol} "
                    f"has_timeframe={has_timeframe} "
                    f"has_close={has_close} "
                    f"has_ts={has_ts} "
                    f"has_feature_state={has_feature_state} "
                    f"ts_col={ts_col} "
                    f"first_ts={first_ts} "
                    f"last_ts={last_ts} "
                    f"verdict={verdict}"
                )

            print("")
            print("INDEX_SYMBOL_PROBE")

            for probe in ("IMOEX", "MOEX", "RTSI", "USD", "USDRUB", "BR", "BRENT"):
                cur.execute("""
                    SELECT COUNT(*)
                    FROM public.feature_snapshots
                    WHERE symbol ILIKE %s;
                """, (f"%{probe}%",))
                cnt = cur.fetchone()[0]
                print(f"PROBE pattern={probe} feature_snapshots_rows={cnt}")

    print("")
    print("SUMMARY")
    print(f"usable_index_sources={candidates}")

    print("")
    print("NEXT_STEPS")
    print("next=MARKET_INDEX_SOURCE_DECISION_V1")

    print("")
    print("VERDICT=MARKET_INDEX_SOURCE_DISCOVERY_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
