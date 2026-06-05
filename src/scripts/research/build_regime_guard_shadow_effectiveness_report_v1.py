#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2


MIN_ROWS_FOR_EFFECTIVENESS = 100


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="24 hours")
    args = parser.parse_args()

    print("=== REGIME GUARD SHADOW EFFECTIVENESS REPORT V1 ===")
    print(f"since={args.since}")
    print(f"min_rows_for_effectiveness={MIN_ROWS_FOR_EFFECTIVENESS}")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute("""
                select exists (
                    select 1
                    from information_schema.tables
                    where table_name='research_regime_guard_shadow'
                );
            """)
            exists = bool(cur.fetchone()[0])
            print(f"TABLE_EXISTS={int(exists)}")

            if not exists:
                print("VERDICT=NO_TABLE")
                return

            cur.execute(
                """
                select
                    count(*) as total_rows,
                    sum(case when would_block then 1 else 0 end) as would_block_rows,
                    sum(case when not would_block then 1 else 0 end) as allow_rows,
                    sum(case when actual_block then 1 else 0 end) as actual_block_rows
                from research_regime_guard_shadow
                where source='regime_guard_shadow_accumulation_v1'
                  and created_at >= now() - %s::interval
                """,
                (args.since,),
            )

            total_rows, would_block_rows, allow_rows, actual_block_rows = cur.fetchone()
            total_rows = int(total_rows or 0)
            would_block_rows = int(would_block_rows or 0)
            allow_rows = int(allow_rows or 0)
            actual_block_rows = int(actual_block_rows or 0)

            block_rate = 0.0 if total_rows == 0 else would_block_rows / total_rows
            allow_rate = 0.0 if total_rows == 0 else allow_rows / total_rows

            print(
                f"TOTAL_ROWS={total_rows} WOULD_BLOCK_ROWS={would_block_rows} "
                f"ALLOW_ROWS={allow_rows} ACTUAL_BLOCK_ROWS={actual_block_rows}"
            )
            print(f"BLOCK_RATE={block_rate:.4f}")
            print(f"ALLOW_RATE={allow_rate:.4f}")

            print()
            print("BY_CLASSIFICATION")
            cur.execute(
                """
                select
                    classification,
                    count(*) as rows,
                    sum(case when would_block then 1 else 0 end) as would_block_rows
                from research_regime_guard_shadow
                where source='regime_guard_shadow_accumulation_v1'
                  and created_at >= now() - %s::interval
                group by classification
                order by rows desc, classification
                """,
                (args.since,),
            )
            for classification, rows, block_rows in cur.fetchall():
                print(
                    f"CLASS_ROW classification={classification} "
                    f"rows={rows} would_block_rows={int(block_rows or 0)}"
                )

            print()
            print("TOP_REGIME_KEYS")
            cur.execute(
                """
                select
                    regime_key,
                    count(*) as rows,
                    sum(case when would_block then 1 else 0 end) as would_block_rows
                from research_regime_guard_shadow
                where source='regime_guard_shadow_accumulation_v1'
                  and created_at >= now() - %s::interval
                group by regime_key
                order by rows desc, regime_key
                limit 20
                """,
                (args.since,),
            )
            for regime_key, rows, block_rows in cur.fetchall():
                print(
                    f"REGIME_ROW regime_key={regime_key} "
                    f"rows={rows} would_block_rows={int(block_rows or 0)}"
                )

    print()

    if total_rows < MIN_ROWS_FOR_EFFECTIVENESS:
        print("VERDICT=INSUFFICIENT_SHADOW_DATA")
    else:
        print("VERDICT=READY_FOR_PNL_CORRELATION")


if __name__ == "__main__":
    main()
