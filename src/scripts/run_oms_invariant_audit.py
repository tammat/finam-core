from __future__ import annotations

import os
import psycopg2


def emit(issue_type: str, payload: str) -> None:
    print(
        f"OMS_INVARIANT_VIOLATION type={issue_type} payload={payload}",
        flush=True,
    )


def main() -> int:
    dsn = os.getenv("DATABASE_URL")

    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    issues = 0

    with conn.cursor() as cur:

        # ---------------------------------------------------------
        # FILLED without broker_order_id
        # ---------------------------------------------------------

        cur.execute("""
            select id, symbol
            from execution_intents
            where intent_state = 'FILLED'
              and execution_mode = 'real'
              and (
                    broker_order_id is null
                    or broker_order_id = ''
              )
        """)

        for intent_id, symbol in cur.fetchall():
            issues += 1

            emit(
                "FILLED_WITHOUT_BROKER_ORDER_ID",
                f"id={intent_id} symbol={symbol}",
            )

        # ---------------------------------------------------------
        # FILLED without qty
        # ---------------------------------------------------------

        cur.execute("""
            select id, symbol
            from execution_intents
            where intent_state = 'FILLED'
              and coalesce(executed_qty, 0) <= 0
        """)

        for intent_id, symbol in cur.fetchall():
            issues += 1

            emit(
                "FILLED_WITHOUT_EXECUTED_QTY",
                f"id={intent_id} symbol={symbol}",
            )

        # ---------------------------------------------------------
        # negative remaining qty
        # ---------------------------------------------------------

        cur.execute("""
            select id, symbol, remaining_qty
            from execution_intents
            where coalesce(remaining_qty, 0) < 0
        """)

        for intent_id, symbol, remaining_qty in cur.fetchall():
            issues += 1

            emit(
                "NEGATIVE_REMAINING_QTY",
                f"id={intent_id} symbol={symbol} remaining_qty={remaining_qty}",
            )

        # ---------------------------------------------------------
        # duplicate FILLED
        # ---------------------------------------------------------

        cur.execute("""
            select
                broker_order_id,
                count(*)
            from execution_intents
            where broker_order_id is not null
              and intent_state = 'FILLED'
            group by broker_order_id
            having count(*) > 1
        """)

        for broker_order_id, cnt in cur.fetchall():
            issues += 1

            emit(
                "DUPLICATE_FILLED_ORDER",
                f"broker_order_id={broker_order_id} count={cnt}",
            )

        # ---------------------------------------------------------
        # impossible qty state
        # ---------------------------------------------------------

        cur.execute("""
            select
                id,
                symbol,
                planned_qty,
                executed_qty
            from execution_intents
            where coalesce(executed_qty,0)
                > coalesce(planned_qty,0)
        """)

        for intent_id, symbol, planned_qty, executed_qty in cur.fetchall():
            issues += 1

            emit(
                "EXECUTED_GT_PLANNED",
                f"id={intent_id} symbol={symbol} "
                f"planned={planned_qty} executed={executed_qty}",
            )

    print(
        f"OMS_INVARIANT_AUDIT_OK issues={issues}",
        flush=True,
    )

    return 0 if issues == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
