from __future__ import annotations

import os
import psycopg2

from finam_core.execution.real_buy_execution_adapter import RealBuyExecutionAdapter


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    real_enabled = os.getenv("REAL_BUY_EXECUTION_ENABLED", "0") == "1"
    kill_switch = os.getenv("REAL_BUY_KILL_SWITCH", "1") == "1"

    max_qty = float(os.getenv("REAL_BUY_MAX_QTY", "100"))
    max_position_value = float(os.getenv("REAL_BUY_MAX_POSITION_VALUE", "30000"))

    conn = psycopg2.connect(dsn)
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
                    coalesce(i.planned_price, (q.raw_json->>'entry_price')::numeric) as planned_price
                from execution_intents i
                left join portfolio_execution_queue q
                    on q.id = i.queue_id
                where i.intent_state in ('READY','RESERVED')
                  and i.execution_mode = 'real'
                order by i.execution_priority asc, i.created_at asc
                limit 10
            """)

            for intent_id, queue_id, symbol, side, qty, planned_price in cur.fetchall():
                processed += 1

                decision = adapter.validate(
                    symbol=str(symbol),
                    side=str(side),
                    qty=float(qty or 0),
                    max_qty=max_qty,
                    max_position_value=max_position_value,
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
                # Здесь будет вызов реального Finam client.place_market_buy/place_limit_buy.
                # До подключения конкретного client API запрещаем фактическую отправку.
                raise RuntimeError(
                    "REAL BUY client call is not wired yet; "
                    "connect Finam order client explicitly before enabling."
                )

    print(
        f"REAL_BUY_EXECUTION_ADAPTER_OK processed={processed} sent={sent} blocked={blocked}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
