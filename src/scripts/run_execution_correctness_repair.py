from __future__ import annotations

import json
import os
import psycopg2


def main() -> int:

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    repaired = 0
    frozen = 0
    archived = 0

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:

            # ============================================================
            # SENT without broker_order_id
            # ============================================================

            cur.execute("""
                update execution_intents
                set
                    intent_state = 'REJECTED',
                    reason = 'repair:missing_broker_order_id',
                    updated_at = now()
                where intent_state = 'SENT'
                  and broker_order_id is null
                returning id
            """)

            rows = cur.fetchall()

            repaired += len(rows)

            if rows:
                print(
                    f"REPAIR_SENT_WITHOUT_BROKER_ORDER_ID repaired={len(rows)}",
                    flush=True,
                )

            # ============================================================
            # negative remaining qty
            # ============================================================

            cur.execute("""
                update execution_intents
                set
                    remaining_qty = 0,
                    updated_at = now(),
                    reason = coalesce(reason,'') || ';repair:negative_remaining_qty'
                where coalesce(remaining_qty,0) < 0
                returning id
            """)

            rows = cur.fetchall()

            repaired += len(rows)

            if rows:
                print(
                    f"REPAIR_NEGATIVE_REMAINING_QTY repaired={len(rows)}",
                    flush=True,
                )

            # ============================================================
            # FILLED qty mismatch
            # ============================================================

            cur.execute("""
                update execution_intents
                set
                    executed_qty = planned_qty,
                    remaining_qty = 0,
                    updated_at = now(),
                    reason = coalesce(reason,'') || ';repair:filled_qty_normalized'
                where intent_state = 'FILLED'
                  and abs(coalesce(planned_qty,0) - coalesce(executed_qty,0)) > 0.0001
                returning id
            """)

            rows = cur.fetchall()

            repaired += len(rows)

            if rows:
                print(
                    f"REPAIR_FILLED_QTY_MISMATCH repaired={len(rows)}",
                    flush=True,
                )

            # ============================================================
            # queue mismatch
            # ============================================================

            cur.execute("""
                update portfolio_execution_queue q
                set
                    queue_state = 'FILLED',
                    updated_at = now()
                from execution_intents i
                where i.queue_id = q.id
                  and i.intent_state = 'FILLED'
                  and q.queue_state <> 'FILLED'
                returning q.id
            """)

            rows = cur.fetchall()

            repaired += len(rows)

            if rows:
                print(
                    f"REPAIR_QUEUE_STATE repaired={len(rows)}",
                    flush=True,
                )

            # ============================================================
            # orphan READY intents older than 24h
            # ============================================================

            cur.execute("""
                update execution_intents
                set
                    intent_state = 'ARCHIVED',
                    updated_at = now(),
                    reason = 'repair:stale_ready_archived'
                where intent_state = 'READY'
                  and created_at < now() - interval '24 hours'
                returning id
            """)

            rows = cur.fetchall()

            archived += len(rows)

            if rows:
                print(
                    f"REPAIR_ARCHIVE_STALE_READY archived={len(rows)}",
                    flush=True,
                )

            # ============================================================
            # impossible states
            # ============================================================

            cur.execute("""
                select count(*)
                from execution_intents
                where
                    intent_state='FILLED'
                    and (
                        coalesce(planned_qty,0) <= 0
                        or coalesce(executed_qty,0) <= 0
                    )
            """)

            impossible = int(cur.fetchone()[0] or 0)

            if impossible > 0:

                cur.execute("""
                    create table if not exists runtime_risk_freeze (
                        id bigserial primary key,
                        created_at timestamptz not null default now(),
                        is_active boolean not null default true,
                        reason text not null,
                        raw_json jsonb not null default '{}'::jsonb
                    )
                """)

                cur.execute("""
                    insert into runtime_risk_freeze (
                        is_active,
                        reason,
                        raw_json
                    )
                    values (
                        true,
                        %s,
                        %s::jsonb
                    )
                """, (
                    "repair:impossible_execution_state",
                    json.dumps({
                        "impossible_execution_states": impossible,
                    }),
                ))

                frozen += 1

                print(
                    f"REPAIR_RUNTIME_FREEZE impossible_states={impossible}",
                    flush=True,
                )

    print(
        "EXECUTION_CORRECTNESS_REPAIR_OK "
        f"repaired={repaired} "
        f"archived={archived} "
        f"frozen={frozen}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
