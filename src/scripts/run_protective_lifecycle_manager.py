from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    symbol = os.getenv("PROTECTIVE_SYMBOL", "SBER@MISX").strip().upper()
    stop_pct = float(os.getenv("PROTECTIVE_STOP_PCT", "0.005"))
    max_qty = float(os.getenv("PROTECTIVE_MAX_QTY", "1"))
    real_armed = os.getenv("PROTECTIVE_REAL_ARMED", "0") == "1"

    execution_mode = "real" if real_armed else "shadow"

    conn = psycopg2.connect(dsn)
    created = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select symbol, qty, avg_price, current_price, updated_at
                from real_portfolio_positions
                where symbol=%s and coalesce(qty,0) > 0
                limit 1
            """, (symbol,))

            row = cur.fetchone()
            if not row:
                print(f"PROTECTIVE_NO_LONG_POSITION symbol={symbol}")
                return 0

            symbol, qty, avg_price, current_price, updated_at = row
            qty = float(qty or 0)
            current_price = float(current_price or 0)
            exit_qty = min(qty, max_qty)

            if exit_qty <= 0 or current_price <= 0:
                print(f"PROTECTIVE_INVALID_INPUT symbol={symbol} qty={qty} price={current_price}")
                return 0

            stop_price = round(current_price * (1 - stop_pct), 4)

            cur.execute("""
                select count(*)
                from execution_intents
                where symbol=%s
                  and side='SELL'
                  and reason in ('protective_stop_shadow','protective_stop_real')
                  and intent_state in ('READY','RESERVED','SENDING','SENT','ACK','RECONCILE_REQUIRED')
            """, (symbol,))

            active = int(cur.fetchone()[0] or 0)
            if active > 0:
                print(f"PROTECTIVE_ALREADY_ACTIVE symbol={symbol} active={active}")
                return 0

            cur.execute("""
                insert into execution_intents (
                    created_at, updated_at, symbol,
                    intent_state, side,
                    planned_qty, remaining_qty,
                    planned_price,
                    execution_priority,
                    execution_mode,
                    reason,
                    raw_json
                )
                values (
                    now(), now(), %s,
                    'RESERVED', 'SELL',
                    %s, %s,
                    %s,
                    1,
                    %s,
                    %s,
                    jsonb_build_object(
                        'order_type','stop',
                        'protective',true,
                        'stop_price',%s,
                        'stop_pct',%s,
                        'raw_qty',%s,
                        'current_price',%s
                    )
                )
            """, (
                symbol,
                exit_qty,
                exit_qty,
                stop_price,
                execution_mode,
                "protective_stop_real" if real_armed else "protective_stop_shadow",
                stop_price,
                stop_pct,
                qty,
                current_price,
            ))

            created = 1

            print(
                f"PROTECTIVE_STOP_INTENT_CREATED symbol={symbol} "
                f"qty={exit_qty} raw_qty={qty} stop={stop_price} "
                f"mode={execution_mode} real_armed={int(real_armed)}",
                flush=True,
            )

    print(f"PROTECTIVE_LIFECYCLE_MANAGER_OK created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
