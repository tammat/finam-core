from __future__ import annotations

import os
import psycopg2

from finam_core.execution.real_buy_execution_adapter import RealBuyExecutionAdapter
from finam_core.execution.finam_order_client_adapter import FinamOrderClientAdapter
from finam_core.execution.execution_intent_transition_service import ExecutionIntentTransitionService



def build_finam_order_client():
    """Русский комментарий: factory реального Finam order client."""
    from finam_core.adapters.grpc.orders_client import FinamOrdersClient
    return FinamOrdersClient()

def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    real_enabled = os.getenv("REAL_BUY_EXECUTION_ENABLED", "0") == "1"
    kill_switch = os.getenv("REAL_BUY_KILL_SWITCH", "1") == "1"

    max_qty = float(os.getenv("REAL_BUY_MAX_QTY", "100"))
    max_position_value = float(os.getenv("REAL_BUY_MAX_POSITION_VALUE", "30000"))

    conn = psycopg2.connect(dsn)
    transition_service = ExecutionIntentTransitionService()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select exists (
                    select 1
                    from runtime_risk_freeze
                    where is_active = true
                      and created_at >= now() - interval '24 hours'
                )
            """)
            db_freeze = bool(cur.fetchone()[0])

    if db_freeze:
        kill_switch = True

    adapter = RealBuyExecutionAdapter()

    processed = 0
    sent = 0
    blocked = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    i.id,
                    i.queue_id,
                    i.symbol,
                    i.side,
                    i.planned_qty,
                    coalesce(i.planned_price, (q.raw_json->>'entry_price')::numeric) as planned_price,
                    coalesce(i.raw_json->>'order_type', q.raw_json->>'order_type', 'limit') as order_type
                from execution_intents i
                left join portfolio_execution_queue q
                    on q.id = i.queue_id
                where i.intent_state in ('READY','RESERVED')
                  and i.execution_mode = 'real'
                order by i.execution_priority asc, i.created_at asc
                limit 10
            """)

            for intent_id, queue_id, symbol, side, qty, planned_price, order_type in cur.fetchall():
                processed += 1

                decision = adapter.validate(
                    symbol=str(symbol),
                    side=str(side),
                    qty=float(qty or 0),
                    max_qty=max_qty,
                    max_position_value=max_position_value,
                    planned_price=float(planned_price or 1 if str(order_type).lower() == "market" else planned_price or 0),
                    kill_switch=kill_switch,
                )

                if not decision.allowed:
                    blocked += 1
                    cur.execute("""
                        update execution_intents
                        set
                            updated_at = now(),
                            reason = %s
                        where id = %s
                    """, (f"real_buy_blocked:{decision.reason}", intent_id))

                    print(
                        "REAL_BUY_BLOCKED "
                        f"intent_id={intent_id} symbol={symbol} reason={decision.reason}",
                        flush=True,
                    )
                    continue

                if not real_enabled:
                    blocked += 1
                    cur.execute("""
                        update execution_intents
                        set
                            updated_at = now(),
                            reason = 'real_buy_dry_run'
                        where id = %s
                    """, (intent_id,))

                    print(
                        "REAL_BUY_DRY_RUN "
                        f"intent_id={intent_id} symbol={symbol} qty={qty} price={planned_price}",
                        flush=True,
                    )
                    continue

                # Русский комментарий:
                # Adapter уже подключён архитектурно, но реальная отправка намеренно заблокирована
                # до финальной проверки сигнатуры Finam client и отдельного боевого флага.
                if os.getenv("REAL_BUY_CLIENT_WIRING_CONFIRMED", "0") != "1":
                    raise RuntimeError(
                        "REAL BUY client wiring is not confirmed; "
                        "set REAL_BUY_CLIENT_WIRING_CONFIRMED=1 only after final method check."
                    )

                first_symbol = os.getenv("FIRST_REAL_ORDER_SYMBOL", "SBER@MISX")

                if str(symbol) != first_symbol:
                    raise RuntimeError(f"FIRST_REAL_ORDER_SYMBOL mismatch: {symbol} != {first_symbol}")

                if float(qty or 0) > 1:
                    raise RuntimeError(f"FIRST_REAL_ORDER qty too high: {qty}")

                if str(order_type).lower() != "market":
                    if float(planned_price or 0) <= 0:
                        raise RuntimeError("FIRST_REAL_ORDER planned_price<=0")

                    if float(planned_price or 0) > float(os.getenv("FIRST_REAL_ORDER_MAX_VALUE", "3000")):
                        raise RuntimeError(f"FIRST_REAL_ORDER planned_price too high: {planned_price}")

                client = build_finam_order_client()

                if str(order_type).lower() == "market":
                    if os.getenv("REAL_BUY_MARKET_ENABLED", "0") != "1":
                        raise RuntimeError("REAL_BUY_MARKET_ENABLED is not enabled")

                    transition_service.transition(
                        cur,
                        intent_id=int(intent_id),
                        next_state="SENDING",
                        reason="real_buy_market_pre_persist_before_broker_call",
                    )

                    print(
                        f"REAL_BUY_MARKET_PRE_PERSIST intent_id={intent_id} "
                        f"symbol={symbol} qty={qty}",
                        flush=True,
                    )

                    import signal

                    def _market_timeout_handler(signum, frame):
                        raise TimeoutError("real_buy_market_order_timeout")

                    signal.signal(signal.SIGALRM, _market_timeout_handler)
                    signal.alarm(int(os.getenv("REAL_MARKET_ORDER_TIMEOUT_SEC", "15")))

                    try:
                        order_result = FinamOrderClientAdapter(client).place_buy_market(
                            symbol=str(symbol),
                            qty=float(qty or 0),
                        )
                    except TimeoutError as exc:
                        cur.execute("""
                            update execution_intents
                            set
                                updated_at = now(),
                                intent_state = 'RECONCILE_REQUIRED',
                                reason = %s
                            where id = %s
                        """, (
                            f"real_buy_market_timeout_reconcile_required:{exc}",
                            intent_id,
                        ))

                        blocked += 1

                        print(
                            f"REAL_BUY_MARKET_TIMEOUT_RECONCILE_REQUIRED "
                            f"intent_id={intent_id} symbol={symbol} qty={qty} reason={exc}",
                            flush=True,
                        )

                        continue
                    finally:
                        signal.alarm(0)
                else:
                    order_result = FinamOrderClientAdapter(client).place_buy_limit(
                        symbol=str(symbol),
                        qty=float(qty or 0),
                        price=float(planned_price or 0),
                    )

                if not order_result.ok:
                    transition_service.transition(
                        cur,
                        intent_id=int(intent_id),
                        next_state="REJECTED",
                        reason=f"real_buy_rejected:{order_result.reason}",
                    )
                    blocked += 1
                    print(
                        f"REAL_BUY_REJECTED intent_id={intent_id} symbol={symbol} reason={order_result.reason}",
                        flush=True,
                    )
                    continue

                transition_service.transition(
                    cur,
                    intent_id=int(intent_id),
                    next_state="SENT",
                    reason="real_buy_sent",
                )

                cur.execute("""
                    update execution_intents
                    set broker_order_id = %s
                    where id = %s
                """, (order_result.broker_order_id, intent_id))

                sent += 1

                print(
                    f"REAL_BUY_SENT intent_id={intent_id} symbol={symbol} qty={qty} "
                    f"price={planned_price} broker_order_id={order_result.broker_order_id}",
                    flush=True,
                )

    print(
        f"REAL_BUY_EXECUTION_ADAPTER_OK processed={processed} sent={sent} blocked={blocked}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
