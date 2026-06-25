#!/usr/bin/env python3

import os
import psycopg2


KEYWORDS = [
    "trade",
    "trades",
    "fill",
    "fills",
    "paper",
    "dry",
    "shadow",
    "replay",
    "outcome",
    "pnl",
    "chain",
]


def main() -> int:
    print("=== HISTORICAL_TRADE_SOURCE_AUDIT_V1_1 ===")
    print("mode=audit_read_only")
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
            print("SOURCE_AUDIT_EXPANDED")

            candidates = []

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
                has_entry_ts = int("entry_ts" in cols)
                has_exit_ts = int("exit_ts" in cols)
                has_net_pnl = int("net_pnl" in cols)
                has_pnl = int("pnl" in cols or "net_pnl" in cols or "gross_pnl" in cols)
                has_payload = int("payload" in cols or "raw_json" in cols)

                cur.execute(f"SELECT COUNT(*) FROM {schema}.{table};")
                rows = cur.fetchone()[0]

                first_ts = None
                last_ts = None
                ts_col = None

                for c in ("entry_ts", "exit_ts", "ts", "created_at", "updated_at"):
                    if c in cols:
                        ts_col = c
                        break

                if ts_col:
                    try:
                        cur.execute(
                            f"SELECT MIN({ts_col}), MAX({ts_col}) FROM {schema}.{table} WHERE {ts_col} IS NOT NULL;"
                        )
                        first_ts, last_ts = cur.fetchone()
                    except Exception:
                        conn.rollback()

                verdict = "NOT_USABLE"
                if rows > 0 and has_symbol and has_entry_ts and has_net_pnl:
                    verdict = "USABLE_CANONICAL_CANDIDATE"
                elif rows > 0 and has_symbol and has_pnl:
                    verdict = "USABLE_NEEDS_TIME_MAPPING"
                elif rows > 0 and has_symbol and has_entry_ts:
                    verdict = "USABLE_NEEDS_PNL_MAPPING"

                if verdict != "NOT_USABLE":
                    candidates.append((schema, table, rows, verdict))

                print(
                    "SOURCE "
                    f"name={schema}.{table} "
                    f"rows={rows} "
                    f"has_symbol={has_symbol} "
                    f"has_timeframe={has_timeframe} "
                    f"has_entry_ts={has_entry_ts} "
                    f"has_exit_ts={has_exit_ts} "
                    f"has_net_pnl={has_net_pnl} "
                    f"has_pnl={has_pnl} "
                    f"has_payload={has_payload} "
                    f"ts_col={ts_col} "
                    f"first_ts={first_ts} "
                    f"last_ts={last_ts} "
                    f"verdict={verdict}"
                )

            print("")
            print("SUMMARY")
            print(f"expanded_candidates={len(candidates)}")
            for schema, table, rows, verdict in sorted(candidates, key=lambda x: x[2], reverse=True):
                print(f"CANDIDATE name={schema}.{table} rows={rows} verdict={verdict}")

    print("")
    print("NEXT_STEPS")
    print("next=HISTORICAL_TRADE_CANONICAL_SOURCE_DECISION_V1")

    print("")
    print("VERDICT=HISTORICAL_TRADE_SOURCE_AUDIT_V1_1_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
