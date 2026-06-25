#!/usr/bin/env python3

import os
import psycopg2


def scalar(cur, sql):
    cur.execute(sql)
    row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    print("=== MARKET_STATE_TRADE_LINKING_VALIDATION_V1 ===")
    print("mode=validation")
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
            total = scalar(cur, "SELECT COUNT(*) FROM research.trade_state_snapshots_v1;")
            ok = scalar(cur, "SELECT COUNT(*) FROM research.trade_state_snapshots_v1 WHERE link_quality='EXACT_OR_NEAREST_OK';")
            entry_only = scalar(cur, "SELECT COUNT(*) FROM research.trade_state_snapshots_v1 WHERE link_quality='ENTRY_ONLY';")
            no_snapshot = scalar(cur, "SELECT COUNT(*) FROM research.trade_state_snapshots_v1 WHERE link_quality='NO_SNAPSHOT';")
            missing_entry_sig = scalar(cur, "SELECT COUNT(*) FROM research.trade_state_snapshots_v1 WHERE link_quality='EXACT_OR_NEAREST_OK' AND entry_compact_signature IS NULL;")
            duplicates = scalar(cur, """
                SELECT COUNT(*) FROM (
                    SELECT trade_id, COUNT(*)
                    FROM research.trade_state_snapshots_v1
                    GROUP BY trade_id
                    HAVING COUNT(*) > 1
                ) q;
            """)

    print("")
    print("SUMMARY")
    print(f"linked_total={total}")
    print(f"link_ok={ok}")
    print(f"entry_only={entry_only}")
    print(f"no_snapshot={no_snapshot}")
    print(f"missing_entry_signature={missing_entry_sig}")
    print(f"duplicates={duplicates}")

    verdict = "MARKET_STATE_TRADE_LINKING_VALIDATION_OK"
    if duplicates:
        verdict = "MARKET_STATE_TRADE_LINKING_VALIDATION_DUPLICATES"
    elif missing_entry_sig:
        verdict = "MARKET_STATE_TRADE_LINKING_VALIDATION_MISSING_ENTRY_SIGNATURE"
    elif not total:
        verdict = "MARKET_STATE_TRADE_LINKING_VALIDATION_NO_ROWS"

    print(f"VERDICT={verdict}")
    return 0 if verdict == "MARKET_STATE_TRADE_LINKING_VALIDATION_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
