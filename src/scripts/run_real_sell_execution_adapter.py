from __future__ import annotations

import os
import psycopg2

from finam_core.execution.real_sell_execution_adapter import RealSellExecutionAdapter
from finam_core.execution.finam_order_client_adapter import FinamOrderClientAdapter


def build_finam_order_client():
    """Русский комментарий: factory реального Finam order client."""
    from finam_core.adapters.grpc.orders_client import FinamOrdersClient
    return FinamOrdersClient()


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    real_enabled = os.getenv("REAL_SELL_EXECUTION_ENABLED", "0") == "1"
    kill_switch = os.getenv("REAL_SELL_KILL_SWITCH", "1") == "1"
    wiring_confirmed = os.getenv("REAL_SELL_CLIENT_WIRING_CONFIRMED", "0") == "1"

    max_qty = float(os.getenv("REAL_SELL_MAX_QTY", "1"))

    conn = psycopg2.connect(dsn)
    adapter = RealSellExecutionAdapter()

    processed = 0
    sent = 0
    blocked = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    i.id,
                    i.symbol,
                    i.side,
                    i.planned_qty,
                    i.planned_price,
                    coalesce(p.qty, 0) as available_qty
                from execution_intents i
                left join real_portfolio_positions p
                    on p.symbol = i.symbol
                where i.intent_state in ('READY','RESERVED')
                  and i.execution_mode = 'real'
                  and i.side = 'SELL'
                order by i.execution_priority asc, i.created_at asc
                limit 5
            """)

            for intent_id, symbol, side, qty, planned_price, available_qty in cur.fetchall():
                processed += 1

                decision = adapter.validate(
                    symbol=str(symbol),
                    side=str(side),
                    qty=float(qty or 0),
                    available_qty=float(available_qty or 0),
                    max_qty=max_qty,
                    planned_price=float(planned_price or 0),
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
                    """, (f"real_sell_blocked:{decision.reason}", intent_id))

                    print(
                        f"REAL_SELL_BLOCKED intent_id={intent_id} symbol={symbol} reason={decision.reason}",
                        flush=True,
                    )
                    continue

                if not real_enabled:
                    blocked += 1
                    cur.execute("""
                        update execution_intents
                        set
                            updated_at = now(),
                            reason = 'real_sell_dry_run'
                        where id = %s
                    """, (intent_id,))

                    print(
                        f"REAL_SELL_DRY_RUN intent_id={intent_id} symbol={symbol} qty={qty} price={planned_price}",
                        flush=True,
                    )
                    continue

                if not wiring_confirmed:
                    raise RuntimeError(
                        "REAL SELL client wiring is not confirmed; "
                        "set REAL_SELL_CLIENT_WIRING_CONFIRMED=1 only after final method check."
                    )

                client = build_finam_order_client()
                order_result = FinamOrderClientAdapter(client).place_buy_limit(
                    symbol=str(symbol),
                    qty=float(qty or 0),
                    price=float(planned_price or 0),
                )

                # Русский комментарий:
                # В v1 FinamOrderClientAdapter пока BUY-only методом.
                # Поэтому реальную SELL-отправку намеренно блокируем до добавления place_sell_limit.
                raise RuntimeError(
                    "REAL SELL live call blocked: add FinamOrderClientAdapter.place_sell_limit first."
                )

    print(
        f"REAL_SELL_EXECUTION_ADAPTER_OK processed={processed} sent={sent} blocked={blocked}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
