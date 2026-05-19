from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    issues: list[str] = []

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            checks = [
                (
                    "FILLED_WITHOUT_BROKER_OR_PAPER_REASON",
                    """
                    select count(*)
                    from execution_intents
                    where intent_state = 'FILLED'
                      and broker_order_id is null
                      and coalesce(reason,'') <> 'paper_fill_simulated'
                    """,
                ),
                (
                    "SENT_WITHOUT_BROKER_ORDER_ID",
                    """
                    select count(*)
                    from execution_intents
                    where intent_state = 'SENT'
                      and broker_order_id is null
                    """,
                ),
                (
                    "FILLED_QTY_MISMATCH",
                    """
                    select count(*)
                    from execution_intents
                    where intent_state = 'FILLED'
                      and abs(coalesce(planned_qty,0) - coalesce(executed_qty,0)) > 0.0001
                    """,
                ),
                (
                    "NEGATIVE_REMAINING_QTY",
                    """
                    select count(*)
                    from execution_intents
                    where coalesce(remaining_qty,0) < 0
                    """,
                ),
                (
                    "QUEUE_READY_WITH_FILLED_INTENT",
                    """
                    select count(*)
                    from portfolio_execution_queue q
                    join execution_intents i on i.queue_id = q.id
                    where i.intent_state = 'FILLED'
                      and q.queue_state <> 'FILLED'
                    """,
                ),
                (
                    "REAL_REJECTED_WITH_EMPTY_REASON",
                    """
                    select count(*)
                    from execution_intents
                    where execution_mode = 'real'
                      and intent_state = 'REJECTED'
                      and coalesce(reason,'') = ''
                    """,
                ),
            ]

            for name, sql in checks:
                cur.execute(sql)
                count = int(cur.fetchone()[0] or 0)

                if count > 0:
                    issues.append(f"{name}={count}")

    if issues:
        print(
            "EXECUTION_CORRECTNESS_AUDIT_FAIL "
            + ";".join(issues),
            flush=True,
        )
        return 1

    print("EXECUTION_CORRECTNESS_AUDIT_OK issues=0", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
