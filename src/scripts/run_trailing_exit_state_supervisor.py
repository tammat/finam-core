from __future__ import annotations

import os
import psycopg2


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    enabled = os.getenv("TRAILING_EXIT_ENABLED", "0") == "1"
    symbol = os.getenv("TRAILING_EXIT_SYMBOL", "SBER@MISX")
    trail_pct = float(os.getenv("TRAILING_EXIT_PCT", "0.01"))
    live_dry_run = os.getenv("TRAILING_EXIT_LIVE_DRY_RUN", "1") == "1"

    if not enabled:
        print("TRAILING_EXIT_DISABLED")
        return 0

    conn = psycopg2.connect(dsn)
    created = 0

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
                select symbol, qty, avg_price, current_price
                from real_portfolio_positions
                where symbol=%s and coalesce(qty,0) > 0
                limit 1
            """, (symbol,))

            row = cur.fetchone()
            if not row:
                print(f"TRAILING_EXIT_NO_LONG_POSITION symbol={symbol}")
                return 0

            symbol, qty, avg_price, current_price = row
            qty = float(qty or 0)
            avg_price = float(avg_price or 0)
            current_price = float(current_price or 0)

            cur.execute("""
                insert into trailing_exit_state (
                    symbol, qty, avg_price,
                    highest_price_since_entry,
                    trailing_stop_price,
                    trail_pct,
                    is_active,
                    updated_at
                )
                values (
                    %s,%s,%s,%s,%s,%s,true,now()
                )
                on conflict (symbol) do update
                set
                    qty=excluded.qty,
                    avg_price=excluded.avg_price,
                    highest_price_since_entry=greatest(
                        trailing_exit_state.highest_price_since_entry,
                        excluded.highest_price_since_entry
                    ),
                    trailing_stop_price=round(
                        greatest(
                            trailing_exit_state.highest_price_since_entry,
                            excluded.highest_price_since_entry
                        ) * (1 - excluded.trail_pct),
                        4
                    ),
                    trail_pct=excluded.trail_pct,
                    is_active=true,
                    updated_at=now()
                returning highest_price_since_entry, trailing_stop_price
            """, (
                symbol,
                qty,
                avg_price,
                current_price,
                round(current_price * (1 - trail_pct), 4),
                trail_pct,
            ))

            high, stop = cur.fetchone()
            high = float(high)
            stop = float(stop)

            print(
                f"TRAILING_EXIT_STATE symbol={symbol} qty={qty} "
                f"current={current_price} high={high} stop={stop}",
                flush=True,
            )

            if current_price > stop:
                print(f"TRAILING_EXIT_HOLD symbol={symbol}")
                return 0

            if live_dry_run:
                print(
                    f"TRAILING_EXIT_LIVE_DRY_RUN_WOULD_CREATE_SELL "
                    f"symbol={symbol} qty={qty} stop={stop} high={high} current={current_price}",
                    flush=True,
                )
                print("TRAILING_EXIT_STATE_SUPERVISOR_OK created=0 live_dry_run=1", flush=True)
                return 0

            cur.execute("""
                select count(*)
                from execution_intents
                where symbol=%s
                  and side='SELL'
                  and execution_mode='real'
                  and intent_state in ('READY','RESERVED','SENDING','SENT','ACK','RECONCILE_REQUIRED')
            """, (symbol,))

            active = int(cur.fetchone()[0] or 0)
            if active > 0:
                print(f"TRAILING_EXIT_ALREADY_ACTIVE symbol={symbol} active={active}")
                return 0

            cur.execute("""
                insert into execution_intents (
                    created_at, updated_at, symbol,
                    intent_state, side,
                    planned_qty, remaining_qty,
                    execution_priority, execution_mode,
                    reason, raw_json
                )
                values (
                    now(), now(), %s,
                    'RESERVED', 'SELL',
                    %s, %s,
                    1, 'real',
                    'trailing_exit_state_market_sell',
                    jsonb_build_object(
                        'order_type','market',
                        'trailing_stop_price',%s,
                        'highest_price_since_entry',%s,
                        'trail_pct',%s
                    )
                )
            """, (symbol, qty, qty, stop, high, trail_pct))

            created = 1
            print(f"TRAILING_EXIT_INTENT_CREATED symbol={symbol} qty={qty} stop={stop}")

    print(f"TRAILING_EXIT_STATE_SUPERVISOR_OK created={created} live_dry_run={int(live_dry_run)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
