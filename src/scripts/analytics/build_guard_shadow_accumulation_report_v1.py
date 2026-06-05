#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def fetch_count(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def print_group(cur, title: str, group_column: str, since: str, limit: int = 10):
    print()
    print(title)
    sql = f"""
        select {group_column}, count(*) as rows
        from guard_shadow_accumulation
        where created_at >= now() - %s::interval
          and source = 'guard_shadow_accumulation_v1'
        group by {group_column}
        order by rows desc, {group_column}
        limit %s
    """
    cur.execute(sql, (since, limit))
    rows = cur.fetchall()

    if not rows:
        print("none")
        return

    for key, cnt in rows:
        print(f"GROUP_ROW {group_column}={key} rows={cnt}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="24 hours")
    args = parser.parse_args()

    print("=== GUARD SHADOW ACCUMULATION REPORT V1 ===")
    print(f"since={args.since}")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute("""
                select to_regclass('public.guard_shadow_accumulation')
            """)
            exists = cur.fetchone()[0]

            if not exists:
                print("TABLE_EXISTS=0")
                print("TOTAL_EVENTS=0")
                print("VERDICT=NO_TABLE_YET")
                return

            total = fetch_count(
                cur,
                """
                select count(*)
                from guard_shadow_accumulation
                where created_at >= now() - %s::interval
                  and source = 'guard_shadow_accumulation_v1'
                """,
                (args.since,),
            )

            would_block = fetch_count(
                cur,
                """
                select count(*)
                from guard_shadow_accumulation
                where created_at >= now() - %s::interval
                  and source = 'guard_shadow_accumulation_v1'
                  and would_block = true
                """,
                (args.since,),
            )

            actual_block = fetch_count(
                cur,
                """
                select count(*)
                from guard_shadow_accumulation
                where created_at >= now() - %s::interval
                  and source = 'guard_shadow_accumulation_v1'
                  and actual_block = true
                """,
                (args.since,),
            )

            block_ready = fetch_count(
                cur,
                """
                select count(*)
                from guard_shadow_accumulation
                where created_at >= now() - %s::interval
                  and source = 'guard_shadow_accumulation_v1'
                  and classification = 'BLOCK_READY'
                """,
                (args.since,),
            )

            block_rate = 0.0 if total == 0 else would_block / total

            print("TABLE_EXISTS=1")
            print(
                f"TOTAL_EVENTS={total} "
                f"WOULD_BLOCK={would_block} "
                f"ACTUAL_BLOCK={actual_block} "
                f"BLOCK_READY={block_ready} "
                f"BLOCK_RATE={block_rate:.4f}"
            )

            print_group(cur, "TOP_SYMBOLS", "symbol", args.since)
            print_group(cur, "TOP_STRATEGIES", "strategy", args.since)
            print_group(cur, "TOP_SESSIONS", "session_bucket", args.since)
            print_group(cur, "TOP_REASONS", "reason", args.since)

    print()
    if total == 0:
        print("VERDICT=NO_SHADOW_ACCUMULATION_EVENTS_YET")
    else:
        print("VERDICT=OK")


if __name__ == "__main__":
    main()
