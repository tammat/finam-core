from __future__ import annotations

import json
import os

import psycopg2

from finam_core.execution.execution_intent_router import (
    ExecutionIntentRouter,
)


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
                    symbol,
                    priority,
                    allocated_qty,
                    decision,
                    allocated_capital
                from portfolio_execution_queue
                where queue_state = 'READY'
                order by priority asc
                limit 20
            """)

            rows = cur.fetchall()

            created = 0

            for row in rows:
                (
                    queue_id,
                    symbol,
                    priority,
                    allocated_qty,
                    decision,
                    allocated_capital,
                ) = row

                allocated_qty = float(allocated_qty or 0)

                if allocated_qty <= 0:
                    continue

                transition = router.transition(
                    current_state="READY",
                    event="RESERVE",
                )

                payload = {
                    "queue_id": queue_id,
                    "symbol": symbol,
                    "decision": decision,
                    "allocated_capital": float(allocated_capital or 0),
                    "planned_qty": allocated_qty,
                    "priority": priority,
                }

                cur.execute("""
                    insert into execution_intents (
                        queue_id,
                        symbol,
                        intent_state,
                        side,
                        planned_qty,
                        executed_qty,
                        remaining_qty,
                        planned_price,
                        execution_priority,
                        execution_mode,
                        reason,
                        raw_json
                    )
                    values (
                        %s,%s,%s,
                        'BUY',
                        %s,
                        0,
                        %s,
                        null,
                        %s,
                        'paper',
                        %s,
                        %s::jsonb
                    )
                    on conflict(queue_id) do update set
                        updated_at = now(),
                        intent_state = excluded.intent_state,
                        remaining_qty = excluded.remaining_qty,
                        execution_priority = excluded.execution_priority,
                        reason = excluded.reason,
                        raw_json = excluded.raw_json
                    returning id
                """, (
                    queue_id,
                    symbol,
                    transition.next_state,
                    allocated_qty,
                    allocated_qty,
                    priority,
                    transition.reason,
                    json.dumps(payload, ensure_ascii=False),
                ))

                created += 1

                cur.execute("""
                    update portfolio_execution_queue
                    set
                        updated_at = now(),
                        queue_state = 'RESERVED'
                    where id = %s
                """, (queue_id,))

                print(
                    "EXECUTION_INTENT_CREATED "
                    f"queue_id={queue_id} "
                    f"symbol={symbol} "
                    f"state={transition.next_state} "
                    f"qty={allocated_qty} "
                    f"priority={priority}",
                    flush=True,
                )

    print(
        f"EXECUTION_INTENT_ROUTER_OK created={created}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
