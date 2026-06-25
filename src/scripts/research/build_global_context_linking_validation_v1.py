#!/usr/bin/env python3

import os
import psycopg2

EXPECTED_CONTEXTS = ("FX_USDRUB", "ENERGY_BR")


def main():

    print("=== GLOBAL_CONTEXT_LINKING_VALIDATION_V1 ===")
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
                SELECT COUNT(*)
                FROM research.trade_state_snapshots_v1
                WHERE link_quality='EXACT_OR_NEAREST_OK';
            """)
            linked_trades = cur.fetchone()[0]

            cur.execute("""
                SELECT
                    context_code,
                    COUNT(*)
                FROM research.market_state_index_context_links_v1
                GROUP BY context_code
                ORDER BY context_code;
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT
                        trade_state_id,
                        context_code,
                        COUNT(*)
                    FROM research.market_state_index_context_links_v1
                    GROUP BY trade_state_id, context_code
                    HAVING COUNT(*)>1
                ) q;
            """)
            duplicates = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM research.market_state_index_context_links_v1
                WHERE link_quality<>'EXACT_OR_NEAREST_OK';
            """)
            bad_links = cur.fetchone()[0]

    print("")
    print("SUMMARY")
    print(f"linked_trades={linked_trades}")

    total_links = 0

    for context_code, cnt in rows:
        total_links += cnt
        print(f"context={context_code} links={cnt}")

    print(f"context_links_total={total_links}")
    print(f"duplicates={duplicates}")
    print(f"bad_links={bad_links}")

    expected_links = linked_trades * len(EXPECTED_CONTEXTS)

    print(f"expected_links={expected_links}")

    verdict = "GLOBAL_CONTEXT_LINKING_VALIDATION_OK"

    if duplicates:
        verdict = "GLOBAL_CONTEXT_LINKING_DUPLICATES"

    elif bad_links:
        verdict = "GLOBAL_CONTEXT_LINKING_BAD_LINKS"

    elif total_links != expected_links:
        verdict = "GLOBAL_CONTEXT_LINKING_INCOMPLETE"

    print("")
    print(f"VERDICT={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
