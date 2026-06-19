#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row


FX_CLASS_BY_SYMBOL = {
    "USDRUBF@RTSX": "FX_FUTURES",
    "CNYRUBF@RTSX": "FX_FUTURES",
    "CNYRUB_TOM@MISX": "FX_SPOT",
}


def main() -> int:
    print("=== MULTI ASSET FX HISTORY ASSET CLASS BACKFILL V1 ===")
    print("mode=analytics_backfill")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("real_execution=0")

    apply = os.getenv("APPLY_FIX", "0") == "1"
    print(f"apply_fix={int(apply)}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    total_planned = 0
    total_updated = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            print()
            print("BEFORE_ROWS")
            cur.execute(
                """
                select
                  symbol,
                  asset_class,
                  timeframe,
                  role,
                  count(*)::int as rows,
                  min(created_at) as first_seen,
                  max(created_at) as last_seen
                from analytics_multi_asset_breakout_row_v1
                where symbol in ('USDRUBF@RTSX','CNYRUBF@RTSX','CNYRUB_TOM@MISX')
                group by symbol, asset_class, timeframe, role
                order by symbol, asset_class, timeframe, role
                """
            )
            for r in cur.fetchall():
                print(
                    "BEFORE_ROW "
                    f"symbol={r['symbol']} asset_class={r['asset_class']} "
                    f"timeframe={r['timeframe']} role={r['role']} rows={r['rows']} "
                    f"first_seen={r['first_seen']} last_seen={r['last_seen']}"
                )

            print()
            print("BACKFILL_PLAN_ROWS")
            for symbol, target_class in FX_CLASS_BY_SYMBOL.items():
                cur.execute(
                    """
                    select count(*)::int as planned
                    from analytics_multi_asset_breakout_row_v1
                    where symbol = %(symbol)s
                      and asset_class is distinct from %(target_class)s
                    """,
                    {"symbol": symbol, "target_class": target_class},
                )
                planned = int(cur.fetchone()["planned"] or 0)
                total_planned += planned

                print(
                    "BACKFILL_PLAN_ROW "
                    f"symbol={symbol} target_asset_class={target_class} planned_updates={planned}"
                )

                if apply and planned > 0:
                    cur.execute(
                        """
                        update analytics_multi_asset_breakout_row_v1
                        set asset_class = %(target_class)s
                        where symbol = %(symbol)s
                          and asset_class is distinct from %(target_class)s
                        """,
                        {"symbol": symbol, "target_class": target_class},
                    )
                    total_updated += cur.rowcount

            if apply:
                conn.commit()
            else:
                conn.rollback()

            print()
            print("AFTER_ROWS")
            cur.execute(
                """
                select
                  symbol,
                  asset_class,
                  timeframe,
                  role,
                  count(*)::int as rows,
                  min(created_at) as first_seen,
                  max(created_at) as last_seen
                from analytics_multi_asset_breakout_row_v1
                where symbol in ('USDRUBF@RTSX','CNYRUBF@RTSX','CNYRUB_TOM@MISX')
                group by symbol, asset_class, timeframe, role
                order by symbol, asset_class, timeframe, role
                """
            )
            for r in cur.fetchall():
                print(
                    "AFTER_ROW "
                    f"symbol={r['symbol']} asset_class={r['asset_class']} "
                    f"timeframe={r['timeframe']} role={r['role']} rows={r['rows']} "
                    f"first_seen={r['first_seen']} last_seen={r['last_seen']}"
                )

    print()
    print("FX_HISTORY_ASSET_CLASS_BACKFILL_SUMMARY")
    print(f"planned_updates={total_planned}")
    print(f"updated_rows={total_updated}")
    print(f"apply_fix={int(apply)}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if apply:
        print("VERDICT=FX_HISTORY_ASSET_CLASS_BACKFILL_APPLIED")
    elif total_planned > 0:
        print("VERDICT=FX_HISTORY_ASSET_CLASS_BACKFILL_PLAN_READY")
    else:
        print("VERDICT=FX_HISTORY_ASSET_CLASS_BACKFILL_NOT_REQUIRED")

    print("MULTI_ASSET_FX_HISTORY_ASSET_CLASS_BACKFILL_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
