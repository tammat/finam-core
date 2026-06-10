#!/usr/bin/env python3
from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


EXPECTED_ALLOW_SYMBOL = "BRM6@RTSX"
EXPECTED_ALLOW_SIDE = "LONG"
EXPECTED_ALLOW_SESSION = "московская_середина"


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== SESSION SIDE EDGE FILTER CANDIDATE AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute("""
                select
                    action,
                    count(*) as rows
                from session_side_edge_filter_candidates_v1
                group by action
                order by action;
            """)

            counts = {
                row["action"]: int(row["rows"])
                for row in cur.fetchall()
            }

            allow_cnt = counts.get("ALLOW", 0)
            block_cnt = counts.get("BLOCK", 0)
            watch_cnt = counts.get("WATCH", 0)

            print("ACTION_COUNTS")
            print(f"ACTION_ROW action=ALLOW rows={allow_cnt}")
            print(f"ACTION_ROW action=BLOCK rows={block_cnt}")
            print(f"ACTION_ROW action=WATCH rows={watch_cnt}")
            print()

            cur.execute("""
                select
                    symbol,
                    side,
                    session,
                    trades,
                    expectancy,
                    profit_factor
                from session_side_edge_filter_candidates_v1
                where action='ALLOW'
                order by symbol, side, session;
            """)

            allow_rows = cur.fetchall()

            print("ALLOW_ROWS")

            for row in allow_rows:
                print(
                    "ALLOW_ROW "
                    f"symbol={row['symbol']} "
                    f"side={row['side']} "
                    f"session={row['session']} "
                    f"trades={row['trades']} "
                    f"expectancy={row['expectancy']} "
                    f"profit_factor={row['profit_factor']}"
                )

            print()

            verdict = "FAIL"

            if (
                allow_cnt == 1
                and block_cnt == 10
                and watch_cnt == 6
                and len(allow_rows) == 1
                and allow_rows[0]["symbol"] == EXPECTED_ALLOW_SYMBOL
                and allow_rows[0]["side"] == EXPECTED_ALLOW_SIDE
                and allow_rows[0]["session"] == EXPECTED_ALLOW_SESSION
            ):
                verdict = "PASS"

            print(
                "AUDIT_SUMMARY "
                f"allow={allow_cnt} "
                f"block={block_cnt} "
                f"watch={watch_cnt} "
                f"expected_allow={EXPECTED_ALLOW_SYMBOL}"
            )

            print(f"AUDIT_VERDICT={verdict}")

            if verdict != "PASS":
                raise SystemExit(1)

    print("SESSION_SIDE_EDGE_FILTER_CANDIDATE_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
