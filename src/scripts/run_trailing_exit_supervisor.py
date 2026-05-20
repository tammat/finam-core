from __future__ import annotations

import os
import psycopg2

from finam_core.execution.trailing_exit_policy import TrailingExitPolicy


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    enabled = os.getenv("TRAILING_EXIT_ENABLED", "0") == "1"
    symbol_filter = os.getenv("TRAILING_EXIT_SYMBOL", "SBER@MISX")
    trail_pct = float(os.getenv("TRAILING_EXIT_PCT", "0.01"))

    if not enabled:
        print("TRAILING_EXIT_DISABLED")
        return 0

    conn = psycopg2.connect(dsn)
    policy = TrailingExitPolicy()

    created = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    symbol,
                    qty,
                    avg_price,
                    current_price
                from real_portfolio_positions
                where symbol = %s
                  and coalesce(qty,0) > 0
                limit 1
            """, (symbol_filter,))

            row = cur.fetchone()
            if not row:
                print(f"TRAILING_EXIT_NO_LONG_POSITION symbol={symbol_filter}")
                return 0

            symbol, qty, avg_price, current_price = row

            decision = policy.decide(
                avg_price=float(avg_price or 0),
                current_price=float(current_price or 0),
                trail_pct=trail_pct,
            )

            print(
                f"TRAILING_EXIT_DECISION symbol={symbol} qty={qty} "
                f"current_price={current_price} stop_price={decision.stop_price} "
                f"exit_required={decision.exit_required} reason={decision.reason}",
                flush=True,
            )

            if not decision.exit_required:
                return 0

            cur.execute("""
                select count(*)
                from execution_intents
                where symbol = %s
                  and side = 'SELL'
                  and execution_mode = 'real'
                  and intent_state in ('READY','RESERVED','SENDING','SENT','ACK','RECONCILE_REQUIRED')
            """, (symbol,))

            active = int(cur.fetchone()[0] or 0)
            if active > 0:
                print(f"TRAILING_EXIT_ALREADY_ACTIVE symbol={symbol} active={active}")
                return 0

            cur.execute("""
                insert into execution_intents (
                    created_at,
                    updated_at,
                    symbol,
                    intent_state,
                    side,
                    planned_qty,
                    remaining_qty,
                    execution_priority,
                    execution_mode,
                    reason,
                    raw_json
                )
                values (
                    now(),
                    now(),
                    %s,
                    'RESERVED',
                    'SELL',
                    %s,
                    %s,
                    1,
                    'real',
                    'trailing_exit_market_sell',
                    jsonb_build_object(
                        'order_type', 'market',
                        'trailing_stop_price', %s,
                        'trail_pct', %s
                    )
                )
            """, (
                symbol,
                qty,
                qty,
                decision.stop_price,
                trail_pct,
            ))

            created += 1
            print(f"TRAILING_EXIT_INTENT_CREATED symbol={symbol} qty={qty}")

    print(f"TRAILING_EXIT_SUPERVISOR_OK created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
