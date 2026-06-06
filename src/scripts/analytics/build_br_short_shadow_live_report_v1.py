#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR SHORT SHADOW LIVE REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("select to_regclass('public.research_br_short_shadow_signals') is not null as exists;")
            table_exists = bool(cur.fetchone()["exists"])

            print(f"TABLE_EXISTS={int(table_exists)}")
            if not table_exists:
                print("VERDICT=NO_TABLE")
                return

            cur.execute("""
                select
                    count(*) as total_rows,
                    count(*) filter (where shadow_logged=true) as shadow_rows,
                    count(*) filter (where reason='br_short_shadow_open_short_candidate') as open_short_candidates,
                    count(*) filter (where reason='br_short_shadow_block_non_canonical_strategy') as non_canonical_blocked,
                    count(*) filter (where reason='br_sell_reduces_existing_long') as reduce_long_rows,
                    max(created_at) as last_created_at
                from research_br_short_shadow_signals;
            """)
            r = cur.fetchone()

            total = int(r["total_rows"] or 0)
            candidates = int(r["open_short_candidates"] or 0)
            blocked = int(r["non_canonical_blocked"] or 0)
            reduce_long = int(r["reduce_long_rows"] or 0)

            print("SUMMARY")
            print(f"TOTAL_ROWS={total}")
            print(f"SHADOW_ROWS={int(r['shadow_rows'] or 0)}")
            print(f"OPEN_SHORT_CANDIDATES={candidates}")
            print(f"NON_CANONICAL_BLOCKED={blocked}")
            print(f"REDUCE_LONG_ROWS={reduce_long}")
            print(f"LAST_CREATED_AT={r['last_created_at']}")
            print()

            print("BY_REASON")
            cur.execute("""
                select reason, count(*) as rows
                from research_br_short_shadow_signals
                group by reason
                order by rows desc, reason;
            """)
            for row in cur.fetchall():
                print(f"REASON_ROW reason={row['reason']} rows={row['rows']}")
            print()

            print("BY_STRATEGY")
            cur.execute("""
                select strategy, reason, count(*) as rows
                from research_br_short_shadow_signals
                group by strategy, reason
                order by strategy, reason;
            """)
            for row in cur.fetchall():
                print(
                    f"STRATEGY_ROW strategy={row['strategy']} "
                    f"reason={row['reason']} rows={row['rows']}"
                )
            print()

            print("LATEST_ROWS")
            cur.execute("""
                select
                    created_at at time zone 'Europe/Moscow' as created_at_msk,
                    symbol, side, strategy, signal_id, mode,
                    allowed, shadow_logged, reason,
                    current_position, price, quantity
                from research_br_short_shadow_signals
                order by created_at desc
                limit 30;
            """)
            for row in cur.fetchall():
                print(
                    "LIVE_ROW "
                    f"created_at_msk={row['created_at_msk']} "
                    f"symbol={row['symbol']} side={row['side']} "
                    f"strategy={row['strategy']} signal_id={row['signal_id']} "
                    f"mode={row['mode']} allowed={int(row['allowed'])} "
                    f"shadow_logged={int(row['shadow_logged'])} "
                    f"reason={row['reason']} position={row['current_position']} "
                    f"price={row['price']} quantity={row['quantity']}"
                )
            print()

    if total == 0:
        print("VERDICT=WAIT_FOR_LIVE_SHADOW_ROWS")
    elif candidates >= 30:
        print("VERDICT=ENOUGH_SHADOW_DATA_FOR_PAPER_CANDIDATE_REVIEW")
    else:
        print("VERDICT=ACCUMULATE_MORE_SHADOW_DATA")


if __name__ == "__main__":
    main()
