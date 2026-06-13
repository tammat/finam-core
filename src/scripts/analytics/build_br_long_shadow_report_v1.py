#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def main() -> None:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")

    print("=== BR LONG SHADOW REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select to_regclass('public.research_br_long_shadow_signals') is not null;
            """)
            exists = bool(cur.fetchone()[0])

            print(f"TABLE_EXISTS={int(exists)}")

            if not exists:
                print("TOTAL_ROWS=0")
                print("VERDICT=NO_TABLE")
                return

            cur.execute("""
                select
                    count(*) as total_rows,
                    count(*) filter (where shadow_logged) as shadow_rows,
                    count(*) filter (where allowed) as allowed_rows,
                    count(*) filter (where not allowed) as blocked_rows
                from research_br_long_shadow_signals;
            """)
            total_rows, shadow_rows, allowed_rows, blocked_rows = cur.fetchone()

            print(
                f"TOTAL_ROWS={int(total_rows or 0)} "
                f"SHADOW_ROWS={int(shadow_rows or 0)} "
                f"ALLOWED_ROWS={int(allowed_rows or 0)} "
                f"BLOCKED_ROWS={int(blocked_rows or 0)}"
            )

            print()
            print("BY_REASON")
            cur.execute("""
                select reason, count(*) as rows
                from research_br_long_shadow_signals
                group by reason
                order by rows desc, reason;
            """)
            for reason, rows in cur.fetchall():
                print(f"REASON_ROW reason={reason} rows={rows}")

            print()
            print("LATEST_ROWS")
            cur.execute("""
                select
                    to_char(created_at at time zone 'Europe/Moscow', 'YYYY-MM-DD HH24:MI:SS') as created_at_msk,
                    symbol,
                    side,
                    strategy,
                    signal_id,
                    mode,
                    allowed,
                    shadow_logged,
                    reason
                from research_br_long_shadow_signals
                order by created_at desc
                limit 20;
            """)
            for row in cur.fetchall():
                created_at_msk, symbol, side, strategy, signal_id, mode, allowed, shadow_logged, reason = row
                print(
                    f"SHADOW_ROW created_at_msk={created_at_msk} symbol={symbol} "
                    f"side={side} strategy={strategy} signal_id={signal_id} "
                    f"mode={mode} allowed={int(allowed)} shadow_logged={int(shadow_logged)} "
                    f"reason={reason}"
                )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
