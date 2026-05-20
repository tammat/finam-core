from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    symbol = os.getenv("TRAILING_EXIT_SYMBOL", "SBER@MISX")
    trail_pct = float(os.getenv("TRAILING_EXIT_PCT", "0.01"))

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                create table if not exists trailing_exit_state (
                    symbol text primary key,
                    qty numeric not null,
                    avg_price numeric not null,
                    highest_price_since_entry numeric not null,
                    trailing_stop_price numeric not null,
                    trail_pct numeric not null,
                    is_active boolean not null default true,
                    updated_at timestamptz not null default now()
                )
            """)
            cur.execute("""
                select
                    symbol,
                    qty,
                    avg_price,
                    current_price,
                    pnl,
                    updated_at
                from real_portfolio_positions
                where symbol = %s
                  and coalesce(qty,0) > 0
                limit 1
            """, (symbol,))

            row = cur.fetchone()

            if not row:
                print(f"TRAILING_DRY_RUN_NO_LONG_POSITION symbol={symbol}", flush=True)
                return 0

            symbol, qty, avg_price, current_price, pnl, pos_updated_at = row

            cur.execute("""
                select
                    highest_price_since_entry,
                    trailing_stop_price,
                    trail_pct,
                    updated_at
                from trailing_exit_state
                where symbol = %s
            """, (symbol,))

            state = cur.fetchone()

            if state:
                old_high, old_stop, old_trail_pct, state_updated_at = state
                high = max(float(old_high or 0), float(current_price or 0))
            else:
                old_high = None
                old_stop = None
                old_trail_pct = None
                state_updated_at = None
                high = float(current_price or 0)

            stop = round(high * (1 - trail_pct), 4)
            exit_required = float(current_price or 0) <= stop

            print(
                "TRAILING_DRY_RUN_AUDIT "
                f"symbol={symbol} "
                f"qty={qty} "
                f"avg_price={avg_price} "
                f"current_price={current_price} "
                f"pnl={pnl} "
                f"old_high={old_high} "
                f"new_high={high} "
                f"old_stop={old_stop} "
                f"new_stop={stop} "
                f"trail_pct={trail_pct} "
                f"exit_required={exit_required} "
                f"position_updated_at={pos_updated_at} "
                f"state_updated_at={state_updated_at}",
                flush=True,
            )

    print("TRAILING_DRY_RUN_AUDIT_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
