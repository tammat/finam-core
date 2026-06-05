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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="24 hours")
    args = parser.parse_args()

    print("=== REGIME GUARD SHADOW REPORT V1 ===")
    print(f"since={args.since}")
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
                    count(*) as total,
                    sum(case when would_block then 1 else 0 end) as would_block,
                    sum(case when actual_block then 1 else 0 end) as actual_block
                from research_regime_guard_shadow
                where created_at >= now() - %s::interval
                """,
                (args.since,),
            )
            total, would_block, actual_block = cur.fetchone()
            total = int(total or 0)
            would_block = int(would_block or 0)
            actual_block = int(actual_block or 0)
            block_rate = 0 if total == 0 else would_block / total

            print(
                f"TOTAL_ROWS={total} WOULD_BLOCK={would_block} "
                f"ACTUAL_BLOCK={actual_block} BLOCK_RATE={block_rate:.4f}"
            )

            print()
            print("BY_CLASSIFICATION")
            cur.execute(
                """
                select classification, count(*) as rows
                from research_regime_guard_shadow
                where created_at >= now() - %s::interval
                group by classification
                order by rows desc, classification
                """,
                (args.since,),
            )
            for classification, rows in cur.fetchall():
                print(f"CLASS_ROW classification={classification} rows={rows}")

            print()
            print("TOP_REGIME_KEYS")
            cur.execute(
                """
                select regime_key, count(*) as rows
                from research_regime_guard_shadow
                where created_at >= now() - %s::interval
                group by regime_key
                order by rows desc, regime_key
                limit 20
                """,
                (args.since,),
            )
            for regime_key, rows in cur.fetchall():
                print(f"REGIME_ROW regime_key={regime_key} rows={rows}")

            print()
            print("TOP_SYMBOLS")
            cur.execute(
                """
                select symbol, count(*) as rows
                from research_regime_guard_shadow
                where created_at >= now() - %s::interval
                group by symbol
                order by rows desc, symbol
                limit 20
                """,
                (args.since,),
            )
            for symbol, rows in cur.fetchall():
                print(f"SYMBOL_ROW symbol={symbol} rows={rows}")

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
