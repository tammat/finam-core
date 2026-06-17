from __future__ import annotations

from finam_core.risk.futures_real_block_guard_v1 import evaluate_futures_real_block_v1

import json
import os
import psycopg2

from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.execution.client_order_id_factory import build_client_order_id


def _extract_order_id(response: dict) -> str:
    return str(
        response.get("order_id")
        or response.get("broker_order_id")
        or response.get("transaction_id")
        or ""
    )


def main() -> int:
    if os.getenv("SYNTHETIC_PROTECTIVE_SELL_ENABLED", "0") != "1":
        print("SYNTH_PROTECTIVE_REAL_SELL_DISABLED reason=SYNTHETIC_PROTECTIVE_SELL_ENABLED")
        return 0

    dry_run = os.getenv("SYNTHETIC_PROTECTIVE_SELL_DRY_RUN", "1") == "1"
    order_type = os.getenv("SYNTHETIC_PROTECTIVE_SELL_ORDER_TYPE", "market").strip().lower()

    if order_type not in {"market", "limit"}:
        print(f"SYNTH_PROTECTIVE_REAL_SELL_INVALID_ORDER_TYPE order_type={order_type}")
        return 0

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    processed = 0
    sent = 0

    conn = psycopg2.connect(dsn)
    client = FinamOrdersClient()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    id,
                    symbol,
                    planned_qty,
                    planned_price,
                    raw_json
                from execution_intents
                where side='SELL'
                  and execution_mode='real'
                  and reason='synthetic_protective_real_sell'
                  and intent_state in ('READY','RESERVED')
                order by id
                limit 10
            """)

            rows = cur.fetchall()

            for intent_id, symbol, planned_qty, planned_price, raw_json in rows:
                processed += 1

                qty = float(planned_qty or 0)
                price = float(planned_price or 0)

                if qty <= 0:
                    print(f"SYNTH_PROTECTIVE_REAL_SELL_INVALID_QTY intent_id={intent_id} qty={qty}")
                    continue

                client_order_id = build_client_order_id(
                    strategy="synthetic_protective",
                    symbol=str(symbol),
                    side="SELL",
                )

                cur.execute("""
                    update execution_intents
                    set
                        intent_state='SENDING',
                        client_order_id=%s,
                        updated_at=now(),
                        raw_json = coalesce(raw_json, '{}'::jsonb) ||
                            jsonb_build_object(
                                'synthetic_protective_sell_adapter', true,
                                'synthetic_protective_order_type', %s,
                                'synthetic_protective_dry_run', %s
                            )
                    where id=%s
                """, (
                    client_order_id,
                    order_type,
                    dry_run,
                    intent_id,
                ))

                print(
                    f"SYNTH_PROTECTIVE_REAL_SELL_SENDING "
                    f"intent_id={intent_id} symbol={symbol} qty={qty} "
                    f"order_type={order_type} dry_run={int(dry_run)} "
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
                                    'synthetic_protective_dry_run_would_send', true,
                                    'dry_run_client_order_id', %s,
                                    'dry_run_qty', %s,
                                    'dry_run_order_type', %s
                                )
                        where id=%s
                    """, (
                        client_order_id,
                        qty,
                        order_type,
                        intent_id,
                    ))

                    print(
                        f"SYNTH_PROTECTIVE_REAL_SELL_DRY_RUN_WOULD_SEND "
                        f"intent_id={intent_id} symbol={symbol} qty={qty} "
                        f"order_type={order_type} client_order_id={client_order_id}",
                        flush=True,
                    )
                    continue

                try:
                    if order_type == "limit":
                        if price <= 0:
                            raise RuntimeError("limit_order_requires_planned_price")

                        # FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_WIRING_V1
                        # Русский комментарий:
                        # Synthetic protective real sell может напрямую вызвать Finam client.
                        # Поэтому перед отправкой заявки блокируем real futures до 01.07.2026.
                        guard_decision = evaluate_futures_real_block_v1(
                            symbol=symbol,
                            execution_mode="real",
                        )
                        if not guard_decision.allowed:
                            print(
                                "FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_BLOCKED "
                                f"intent_id={intent_id} "
                                f"symbol={guard_decision.symbol} "
                                f"mode={guard_decision.execution_mode} "
                                f"kind={guard_decision.instrument_kind} "
                                f"reason={guard_decision.reason} "
                                f"current_date={guard_decision.current_date} "
                                f"allowed_after={guard_decision.allowed_after}",
                                flush=True,
                            )
                            sent = sent + 0
                            blocked = blocked + 1 if 'blocked' in locals() else 1
                            continue

                        response = client.place_limit_order(
                            symbol=str(symbol),
                            side="SELL",
                            qty=qty,
                            limit_price=price,
                            client_order_id=client_order_id,
                        )
                    else:
                        # FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_WIRING_V1
                        # Русский комментарий:
                        # Synthetic protective real sell может напрямую вызвать Finam client.
                        # Поэтому перед отправкой заявки блокируем real futures до 01.07.2026.
                        guard_decision = evaluate_futures_real_block_v1(
                            symbol=symbol,
                            execution_mode="real",
                        )
                        if not guard_decision.allowed:
                            print(
                                "FUTURES_REAL_BLOCK_GUARD_SYNTHETIC_PROTECTIVE_BLOCKED "
                                f"intent_id={intent_id} "
                                f"symbol={guard_decision.symbol} "
                                f"mode={guard_decision.execution_mode} "
                                f"kind={guard_decision.instrument_kind} "
                                f"reason={guard_decision.reason} "
                                f"current_date={guard_decision.current_date} "
                                f"allowed_after={guard_decision.allowed_after}",
                                flush=True,
                            )
                            sent = sent + 0
                            blocked = blocked + 1 if 'blocked' in locals() else 1
                            continue

                        response = client.place_market_order(
                            symbol=str(symbol),
                            side="SELL",
                            qty=qty,
                            price=None,
                            client_order_id=client_order_id,
                        )

                    broker_order_id = _extract_order_id(response)

                    status = str(response.get("status") or "").upper()
                    reason = str(response.get("reason") or "")

                    if status in {"REJECTED", "FAILED", "ERROR"} or not broker_order_id:
                        cur.execute("""
                            update execution_intents
                            set
                                intent_state='REJECTED',
                                updated_at=now(),
                                raw_json = coalesce(raw_json, '{}'::jsonb) ||
                                    jsonb_build_object(
                                        'synthetic_protective_sell_error', %s,
                                        'broker_response', %s::jsonb
                                    )
                            where id=%s
                        """, (
                            reason or status or "empty_broker_order_id",
                            json.dumps(response),
                            intent_id,
                        ))

                        print(
                            f"SYNTH_PROTECTIVE_REAL_SELL_REJECTED "
                            f"intent_id={intent_id} reason={reason or status or 'empty_broker_order_id'}",
                            flush=True,
                        )
                        continue

                    cur.execute("""
                        update execution_intents
                        set
                            intent_state='SENT',
                            broker_order_id=%s,
                            updated_at=now(),
                            raw_json = coalesce(raw_json, '{}'::jsonb) ||
                                jsonb_build_object(
                                    'synthetic_protective_sell_sent', true,
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
                        f"SYNTH_PROTECTIVE_REAL_SELL_SENT "
                        f"intent_id={intent_id} broker_order_id={broker_order_id}",
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
                                    'synthetic_protective_sell_exception',
                                    %s
                                )
                        where id=%s
                    """, (
                        f"{type(exc).__name__}:{exc}",
                        intent_id,
                    ))

                    print(
                        f"SYNTH_PROTECTIVE_REAL_SELL_REJECTED "
                        f"intent_id={intent_id} error={type(exc).__name__}:{exc}",
                        flush=True,
                    )

    print(
        f"SYNTH_PROTECTIVE_REAL_SELL_ADAPTER_OK processed={processed} sent={sent} dry_run={int(dry_run)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
