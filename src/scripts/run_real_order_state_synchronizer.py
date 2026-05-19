from __future__ import annotations

import os
import psycopg2

from finam_core.execution.real_order_state_synchronizer import RealOrderStateSynchronizer
from finam_core.execution.finam_order_status_adapter import FinamOrderStatusAdapter



def build_finam_order_client():
    """Русский комментарий: factory реального Finam order client для чтения статуса заявки."""
    from finam_core.adapters.grpc.orders_client import FinamOrdersClient
    return FinamOrdersClient()

def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    # v1 dry mode: без вызова брокера, пока не подключён get_order_status client.
    broker_sync_enabled = os.getenv("REAL_ORDER_STATE_SYNC_ENABLED", "0") == "1"

    conn = psycopg2.connect(dsn)
    sync = RealOrderStateSynchronizer()

    processed = 0
    updated = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    id,
                    symbol,
                    broker_order_id,
                    intent_state
                from execution_intents
                where execution_mode = 'real'
                  and broker_order_id is not null
                  and intent_state in ('SENT','ACK','PARTIAL_FILL')
                order by updated_at asc
                limit 20
            """)

            rows = cur.fetchall()

            for intent_id, symbol, broker_order_id, intent_state in rows:
                processed += 1

                if not broker_sync_enabled:
                    print(
                        "REAL_ORDER_STATE_SYNC_DRY_RUN "
                        f"intent_id={intent_id} symbol={symbol} broker_order_id={broker_order_id} state={intent_state}",
                        flush=True,
                    )
                    continue

                # Русский комментарий:
                # Adapter подключён архитектурно, но реальный client пока не создаём здесь.
                # Перед включением нужно явно передать/создать Finam client.
                if os.getenv("REAL_ORDER_STATUS_CLIENT_WIRING_CONFIRMED", "0") != "1":
                    raise RuntimeError(
                        "REAL ORDER STATUS client wiring is not confirmed; "
                        "set REAL_ORDER_STATUS_CLIENT_WIRING_CONFIRMED=1 only after final method check."
                    )

                client = build_finam_order_client()

                import signal

                def _timeout_handler(signum, frame):
                    raise TimeoutError("order_status_sync_timeout")

                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(int(os.getenv("REAL_ORDER_STATUS_TIMEOUT_SEC", "10")))

                try:
                    status = FinamOrderStatusAdapter(client).get_status(
                        broker_order_id=str(broker_order_id),
                        symbol=str(symbol),
                    )
                finally:
                    signal.alarm(0)

                if not status.ok:
                    print(
                        f"REAL_ORDER_STATE_SYNC_STATUS_FAIL "
                        f"intent_id={intent_id} symbol={symbol} "
                        f"broker_order_id={broker_order_id} reason={status.reason}",
                        flush=True,
                    )
                    continue

                decision = sync.map_broker_status(
                    broker_status=status.broker_status,
                )

                cur.execute("""
                    update execution_intents
                    set
                        updated_at = now(),
                        intent_state = %s,
                        executed_qty = case
                            when %s > 0 then %s
                            else executed_qty
                        end,
                        remaining_qty = greatest(coalesce(planned_qty,0) - %s, 0),
                        avg_execution_price = case
                            when %s > 0 then %s
                            else avg_execution_price
                        end,
                        reason = %s
                    where id = %s
                """, (
                    decision.intent_state,
                    status.filled_qty,
                    status.filled_qty,
                    status.filled_qty,
                    status.avg_price,
                    status.avg_price,
                    decision.reason,
                    intent_id,
                ))

                updated += 1

                print(
                    f"REAL_ORDER_STATE_SYNC_UPDATE "
                    f"intent_id={intent_id} symbol={symbol} "
                    f"broker_order_id={broker_order_id} "
                    f"broker_status={status.broker_status} "
                    f"intent_state={decision.intent_state} "
                    f"filled_qty={status.filled_qty} "
                    f"avg_price={status.avg_price}",
                    flush=True,
                )

                # broker_status = client.get_order_status(...)
                # decision = sync.map_broker_status(broker_status=broker_status)

                # cur.execute("""
                #     update execution_intents
                #     set
                #         updated_at = now(),
                #         intent_state = %s,
                #         reason = %s
                #     where id = %s
                # """, (decision.intent_state, decision.reason, intent_id))
                # updated += 1

    print(
        f"REAL_ORDER_STATE_SYNCHRONIZER_OK processed={processed} updated={updated}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
