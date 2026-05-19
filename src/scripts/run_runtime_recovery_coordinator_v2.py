from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    recovered_queue = 0
    recovered_intents = 0
    stale_cancelled = 0
    lifecycle_reopened = 0

    with conn:
        with conn.cursor() as cur:
            # 1. READY queue без intent → оставить READY, будет подхвачено router.
            cur.execute("""
                update portfolio_execution_queue q
                set updated_at = now()
                where q.queue_state = 'READY'
                  and not exists (
                      select 1
                      from execution_intents i
                      where i.queue_id = q.id
                  )
            """)
            recovered_queue = cur.rowcount

            # 2. RESERVED queue с отсутствующим intent → вернуть READY.
            cur.execute("""
                update portfolio_execution_queue q
                set
                    queue_state = 'READY',
                    updated_at = now()
                where q.queue_state = 'RESERVED'
                  and not exists (
                      select 1
                      from execution_intents i
                      where i.queue_id = q.id
                  )
            """)
            recovered_queue += cur.rowcount

            # 3. Intent RESERVED старше 30 минут → READY для повторного route.
            cur.execute("""
                update execution_intents
                set
                    intent_state = 'READY',
                    updated_at = now(),
                    reason = 'recovery_reserved_timeout'
                where intent_state = 'RESERVED'
                  and updated_at < now() - interval '30 minutes'
            """)
            recovered_intents += cur.rowcount

            # 4. Intent SENT/ACK слишком старый → REJECTED в paper mode.
            cur.execute("""
                update execution_intents
                set
                    intent_state = 'REJECTED',
                    updated_at = now(),
                    reason = 'recovery_stale_sent_ack'
                where execution_mode = 'paper'
                  and intent_state in ('SENT','ACK')
                  and updated_at < now() - interval '30 minutes'
            """)
            stale_cancelled += cur.rowcount

            # 5. Queue RESERVED, но intent уже FILLED → queue FILLED.
            cur.execute("""
                update portfolio_execution_queue q
                set
                    queue_state = 'FILLED',
                    updated_at = now()
                from execution_intents i
                where i.queue_id = q.id
                  and i.intent_state = 'FILLED'
                  and q.queue_state <> 'FILLED'
            """)
            recovered_queue += cur.rowcount

            # 6. Filled position без lifecycle → lifecycle создаст manager, здесь только логируем кандидатов.
            cur.execute("""
                select count(*)
                from real_portfolio_positions p
                where coalesce(p.qty, 0) > 0
                  and not exists (
                      select 1
                      from position_lifecycle_state l
                      where l.symbol = p.symbol
                        and coalesce(l.remaining_qty, 0) > 0
                  )
            """)
            lifecycle_reopened = int(cur.fetchone()[0] or 0)

    print(
        "RUNTIME_RECOVERY_COORDINATOR_V2_OK "
        f"recovered_queue={recovered_queue} "
        f"recovered_intents={recovered_intents} "
        f"stale_cancelled={stale_cancelled} "
        f"lifecycle_candidates={lifecycle_reopened}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
