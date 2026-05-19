from __future__ import annotations

import os
from decimal import Decimal

import psycopg2

from finam_core.execution.execution_intent_router import ExecutionIntentRouter


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)
    router = ExecutionIntentRouter()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    id,
                    queue_id,
                    symbol,
                    intent_state,
                    planned_qty,
                    remaining_qty,
                    execution_priority
                from execution_intents
                where execution_mode = 'paper'
                  and intent_state in ('RESERVED','SENT','ACK','PARTIAL_FILL')
                order by execution_priority asc, created_at asc
                limit 20
            """)

            rows = cur.fetchall()
            filled = 0

            for row in rows:
                intent_id, queue_id, symbol, state, planned_qty, remaining_qty, priority = row

                planned_qty = Decimal(str(planned_qty or 0))
                remaining_qty = Decimal(str(remaining_qty or 0))

                if planned_qty <= 0 or remaining_qty <= 0:
                    continue

                # Русский комментарий: v1 paper-fill исполняет весь остаток сразу.
                sent = router.transition(current_state=state, event="SEND")
                ack = router.transition(current_state=sent.next_state, event="ACK")
                fill = router.transition(current_state=ack.next_state, event="FILL")

                cur.execute("""
                    select entry_price
                    from radar_candidate_analysis
                    where symbol = %s
                      and source = 'watch_candidate_runtime_analyzer'
                      and decision = 'ALERT'
                    order by created_at desc
                    limit 1
                """, (symbol,))
                price_row = cur.fetchone()

                fill_price = Decimal(str(price_row[0] if price_row and price_row[0] is not None else 0))

                cur.execute("""
                    update execution_intents
                    set
                        updated_at = now(),
                        intent_state = %s,
                        executed_qty = planned_qty,
                        remaining_qty = 0,
                        avg_execution_price = %s,
                        reason = %s
                    where id = %s
                """, (
                    fill.next_state,
                    fill_price,
                    "paper_fill_simulated",
                    intent_id,
                ))

                cur.execute("""
                    update portfolio_execution_queue
                    set
                        updated_at = now(),
                        queue_state = 'FILLED'
                    where id = %s
                """, (queue_id,))

                print(
                    "EXECUTION_INTENT_PAPER_FILLED "
                    f"intent_id={intent_id} "
                    f"queue_id={queue_id} "
                    f"symbol={symbol} "
                    f"qty={planned_qty} "
                    f"price={fill_price} "
                    f"priority={priority}",
                    flush=True,
                )

                filled += 1

    print(f"EXECUTION_INTENT_FILL_SIMULATOR_OK filled={filled}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
