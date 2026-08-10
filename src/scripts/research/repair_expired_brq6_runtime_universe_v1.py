from __future__ import annotations

import argparse
from datetime import date

import psycopg2
import psycopg2.extras


DB = "postgresql:///finam_core"

EXPIRED_SYMBOL = "BRQ6@RTSX"
SUCCESSOR_SYMBOL = "BRU6@RTSX"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(DB) as conn:
        conn.autocommit = False

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            # Последняя доказанная MOEX-спецификация BRQ6.
            cur.execute(
                """
                SELECT
                    symbol,
                    source_payload->>'LASTTRADEDATE'
                        AS last_trade_date
                FROM analytics.contract_spec_sync_item_v1
                WHERE symbol=%s
                  AND status_code IN (
                      'CREATED',
                      'UPDATED',
                      'UNCHANGED'
                  )
                  AND source_payload <> '{}'::jsonb
                  AND source_payload ? 'LASTTRADEDATE'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (EXPIRED_SYMBOL,),
            )

            spec = cur.fetchone()

            if not spec:
                raise RuntimeError(
                    "ERROR=BRQ6_LAST_TRADE_DATE_NOT_FOUND"
                )

            last_trade_date = date.fromisoformat(
                spec["last_trade_date"]
            )

            cur.execute(
                """
                SELECT symbol,is_enabled
                FROM runtime_active_universe
                WHERE symbol IN (%s,%s)
                ORDER BY symbol
                """,
                (
                    EXPIRED_SYMBOL,
                    SUCCESSOR_SYMBOL,
                ),
            )

            universe = {
                row["symbol"]: bool(row["is_enabled"])
                for row in cur.fetchall()
            }

            brq6_active = universe.get(
                EXPIRED_SYMBOL,
                False,
            )
            bru6_active = universe.get(
                SUCCESSOR_SYMBOL,
                False,
            )

            expired = last_trade_date < date.today()

            print(
                "BRQ6_LIFECYCLE_ROW "
                f"symbol={EXPIRED_SYMBOL} "
                f"last_trade_date={last_trade_date} "
                f"today={date.today()} "
                f"expired={int(expired)} "
                f"runtime_active={int(brq6_active)}"
            )

            print(
                "SUCCESSOR_ROW "
                f"symbol={SUCCESSOR_SYMBOL} "
                f"runtime_active={int(bru6_active)}"
            )

            if not expired:
                raise RuntimeError(
                    "ERROR=BRQ6_NOT_EXPIRED"
                )

            if not brq6_active:
                print("repair_required=0")
                print("already_disabled=1")
                conn.rollback()

            else:
                if not bru6_active:
                    raise RuntimeError(
                        "ERROR=ACTIVE_BRENT_SUCCESSOR_NOT_CONFIRMED"
                    )

                print("repair_required=1")

                if args.apply:
                    cur.execute(
                        """
                        UPDATE runtime_active_universe
                        SET is_enabled=false
                        WHERE symbol=%s
                          AND is_enabled=true
                        """,
                        (EXPIRED_SYMBOL,),
                    )

                    if cur.rowcount != 1:
                        raise RuntimeError(
                            "ERROR=BRQ6_DISABLE_ROWCOUNT_MISMATCH"
                        )

                    conn.commit()

                    print("db_writes_performed=1")
                    print("brq6_disabled=1")
                else:
                    conn.rollback()

                    print("db_writes_performed=0")
                    print("brq6_disabled=0")
                    print("dry_run=1")

    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("real_trading_enabled=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EXPIRED_BRQ6_RUNTIME_UNIVERSE_REPAIR_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
