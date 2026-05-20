from __future__ import annotations

import json
import os
import psycopg2

from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.execution.client_order_id_factory import build_client_order_id


ACTIVE_STATES = (
    "READY",
    "RESERVED",
)


def main() -> int:
    if os.getenv("PROTECTIVE_REAL_ARMED", "0") != "1":
        print("PROTECTIVE_REAL_EXECUTION_DISABLED reason=PROTECTIVE_REAL_ARMED")
        return 0

    if os.getenv("REAL_SELL_STOP_ENABLED", "0") != "1":
        print("PROTECTIVE_REAL_EXECUTION_DISABLED reason=REAL_SELL_STOP_ENABLED")
        return 0

    dry_run = os.getenv("PROTECTIVE_REAL_DRY_RUN", "1") == "1"

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    processed = 0
    sent = 0

    client = FinamOrdersClient()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    id,
                    symbol,
                    planned_qty,
                    planned_price,
                    execution_mode,
                    raw_json
                from execution_intents
                where side='SELL'
                  and reason='protective_stop_real'
                  and execution_mode='real'
                  and intent_state in ('READY','RESERVED')
                order by id
                limit 10
            """)

            rows = cur.fetchall()

            for row in rows:
                (
                    intent_id,
                    symbol,
                    planned_qty,
                    planned_price,
                    execution_mode,
                    raw_json,
                ) = row

                processed += 1

                qty = float(planned_qty or 0)
                stop_price = float(planned_price or 0)

                if qty <= 0 or stop_price <= 0:
                    print(
                        f"PROTECTIVE_REAL_INVALID_INPUT "
                        f"intent_id={intent_id} qty={qty} stop={stop_price}",
                        flush=True,
                    )
                    continue

                client_order_id = build_client_order_id(
                    strategy="protective",
                    symbol=symbol,
                    side="SELL",
                )

                cur.execute("""
                    update execution_intents
                    set
                        intent_state='SENDING',
                        updated_at=now(),
                        client_order_id=%s
                    where id=%s
                """, (
                    client_order_id,
                    intent_id,
                ))

                print(
                    f"PROTECTIVE_REAL_SENDING "
                    f"intent_id={intent_id} symbol={symbol} "
                    f"qty={qty} stop={stop_price} "
                    f"client_order_id={client_order_id}",
                    flush=True,
                )

                if dry_run:
                    cur.execute("""
                        update execution_intents
                        set
                            intent_state='RESERVED',
                            updated_at=now(),
                            raw_json = coalesce(raw_json, '{}'::jsonb) ||
                                jsonb_build_object(
                                    'protective_real_dry_run', true,
                                    'dry_run_client_order_id', %s,
                                    'dry_run_stop_price', %s,
                                    'dry_run_qty', %s
                                )
                        where id=%s
                    """, (
                        client_order_id,
                        stop_price,
                        qty,
                        intent_id,
                    ))

                    print(
                        f"PROTECTIVE_REAL_DRY_RUN_WOULD_SEND "
                        f"intent_id={intent_id} symbol={symbol} "
                        f"qty={qty} stop={stop_price} client_order_id={client_order_id}",
                        flush=True,
                    )

                    continue

                try:
                    response = client.place_stop_order(
                        symbol=symbol,
                        side="SELL",
                        qty=qty,
                        stop_price=stop_price,
                        client_order_id=client_order_id,
                    )

                    broker_order_id = str(
                        response.get("transaction_id")
                        or response.get("order_id")
                        or response.get("stop_id")
                        or ""
                    )

                    cur.execute("""
                        update execution_intents
                        set
                            intent_state='SENT',
                            updated_at=now(),
                            broker_order_id=%s,
                            raw_json = coalesce(raw_json, '{}'::jsonb) ||
                                jsonb_build_object(
                                    'protective_stop_sent', true,
                                    'broker_response', %s::jsonb
                                )
                        where id=%s
                    """, (
                        broker_order_id,
                        json.dumps(response),
                        intent_id,
                    ))

                    sent += 1

                    print(
                        f"PROTECTIVE_REAL_SENT "
                        f"intent_id={intent_id} "
                        f"broker_order_id={broker_order_id}",
                        flush=True,
                    )

                except Exception as exc:
                    cur.execute("""
                        update execution_intents
                        set
                            intent_state='REJECTED',
                            updated_at=now(),
                            raw_json = coalesce(raw_json, '{}'::jsonb) ||
                                jsonb_build_object(
                                    'protective_stop_error', %s
                                )
                        where id=%s
                    """, (
                        str(exc),
                        intent_id,
                    ))

                    print(
                        f"PROTECTIVE_REAL_REJECTED "
                        f"intent_id={intent_id} "
                        f"error={type(exc).__name__}:{exc}",
                        flush=True,
                    )

    print(
        f"PROTECTIVE_STOP_REAL_EXECUTION_ADAPTER_OK "
        f"processed={processed} sent={sent} dry_run={int(dry_run)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
