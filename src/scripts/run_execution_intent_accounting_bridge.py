from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")

    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
                select
                    id,
                    symbol,
                    planned_qty,
                    avg_execution_price
                from execution_intents
                where intent_state = 'FILLED'
                  and coalesce(raw_json->>'accounted','false') != 'true'
                order by created_at asc
                limit 20
            """)

            rows = cur.fetchall()

            accounted = 0

            for row in rows:
                (
                    intent_id,
                    symbol,
                    planned_qty,
                    avg_execution_price,
                ) = row

                qty = Decimal(str(planned_qty or 0))
                price = Decimal(str(avg_execution_price or 0))

                if qty <= 0 or price <= 0:
                    continue

                market_value = qty * price

                # Русский комментарий:
                # Обновляем paper positions.

                cur.execute("""
                    insert into real_portfolio_positions (
                        symbol,
                        qty,
                        avg_price,
                        current_price,
                        market_value,
                        pnl,
                        pnl_day,
                        currency,
                        source,
                        raw_json
                    )
                    values (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        0,
                        0,
                        'RUB',
                        'paper_execution_bridge',
                        %s::jsonb
                    )
                    on conflict(symbol) do update set
                        qty = real_portfolio_positions.qty + excluded.qty,
                        avg_price = excluded.avg_price,
                        current_price = excluded.current_price,
                        market_value =
                            (real_portfolio_positions.qty + excluded.qty)
                            * excluded.current_price,
                        updated_at = now(),
                        raw_json = excluded.raw_json
                """, (
                    symbol,
                    qty,
                    price,
                    price,
                    market_value,
                    json.dumps({
                        "intent_id": intent_id,
                        "bridge": "execution_intent_accounting_bridge",
                    }),
                ))

                # Русский комментарий:
                # Помечаем intent как учтённый.

                cur.execute("""
                    update execution_intents
                    set
                        updated_at = now(),
                        raw_json = jsonb_set(
                            raw_json,
                            '{accounted}',
                            'true'::jsonb,
                            true
                        )
                    where id = %s
                """, (intent_id,))

                print(
                    "EXECUTION_ACCOUNTING_APPLIED "
                    f"intent_id={intent_id} "
                    f"symbol={symbol} "
                    f"qty={qty} "
                    f"price={price}",
                    flush=True,
                )

                accounted += 1

    print(
        f"EXECUTION_INTENT_ACCOUNTING_BRIDGE_OK accounted={accounted}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
