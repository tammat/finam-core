#!/usr/bin/env python3

import os
import psycopg2


CANDIDATE_TABLES = [
    ("public", "trade_outcomes"),
    ("public", "closed_trade_chains_v3"),
    ("public", "v_trades_pnl_paired_grafana"),
    ("public", "virtual_signal_trades"),
    ("public", "analytics_intrabar_trade_quality"),
    ("public", "strategy_exit_alpha_bar_replay"),
]


def table_exists(cur, schema: str, table: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema=%s
              AND table_name=%s
        );
        """,
        (schema, table),
    )
    return bool(cur.fetchone()[0])


def columns(cur, schema: str, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema=%s
          AND table_name=%s
        ORDER BY ordinal_position;
        """,
        (schema, table),
    )
    return [r[0] for r in cur.fetchall()]


def main() -> int:
    print("=== HISTORICAL_TRADE_SOURCE_AUDIT_V1 ===")
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
            print("")
            print("SOURCE_AUDIT")

            usable = 0

            for schema, table in CANDIDATE_TABLES:
                full = f"{schema}.{table}"

                if not table_exists(cur, schema, table):
                    print(f"SOURCE name={full} exists=0 rows=0 verdict=NOT_FOUND")
                    continue

                cols = columns(cur, schema, table)

                has_symbol = "symbol" in cols
                has_entry_ts = "entry_ts" in cols
                has_exit_ts = "exit_ts" in cols
                has_net_pnl = "net_pnl" in cols
                has_timeframe = "timeframe" in cols

                cur.execute(f"SELECT COUNT(*) FROM {schema}.{table};")
                rows_total = cur.fetchone()[0]

                date_col = "entry_ts" if has_entry_ts else None
                first_ts = None
                last_ts = None

                if date_col:
                    cur.execute(
                        f"""
                        SELECT MIN({date_col}), MAX({date_col})
                        FROM {schema}.{table}
                        WHERE {date_col} IS NOT NULL;
                        """
                    )
                    first_ts, last_ts = cur.fetchone()

                verdict = "NOT_USABLE"
                if rows_total and has_symbol and has_entry_ts and has_net_pnl:
                    verdict = "USABLE_CANONICAL_CANDIDATE"
                    usable += 1
                elif rows_total and has_symbol and has_entry_ts:
                    verdict = "USABLE_NEEDS_PNL_MAPPING"

                print(
                    "SOURCE "
                    f"name={full} "
                    f"exists=1 "
                    f"rows={rows_total} "
                    f"has_symbol={int(has_symbol)} "
                    f"has_timeframe={int(has_timeframe)} "
                    f"has_entry_ts={int(has_entry_ts)} "
                    f"has_exit_ts={int(has_exit_ts)} "
                    f"has_net_pnl={int(has_net_pnl)} "
                    f"first_ts={first_ts} "
                    f"last_ts={last_ts} "
                    f"verdict={verdict}"
                )

            print("")
            print("SUMMARY")
            print(f"candidate_sources={len(CANDIDATE_TABLES)}")
            print(f"usable_canonical_candidates={usable}")

    print("")
    print("NEXT_STEPS")
    print("next=HISTORICAL_TRADE_CANONICAL_SOURCE_DECISION_V1")

    print("")
    print("VERDICT=HISTORICAL_TRADE_SOURCE_AUDIT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
