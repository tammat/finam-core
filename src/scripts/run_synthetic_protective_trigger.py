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
    armed = os.getenv("SYNTHETIC_PROTECTIVE_ARMED", "0") == "1"
    live_dry_run = os.getenv("SYNTHETIC_PROTECTIVE_DRY_RUN", "1") == "1"
    force_trigger = os.getenv("SYNTHETIC_PROTECTIVE_FORCE_TRIGGER", "0") == "1"

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
                print(f"SYNTH_PROTECTIVE_NO_POSITION symbol={symbol}")
                return 0

            symbol, qty, avg_price, current_price, updated_at = row
            qty = float(qty or 0)
            avg_price = float(avg_price or 0)
            current_price = float(current_price or 0)
            exit_qty = min(qty, max_qty)

            stop_price = round(avg_price * (1 - stop_pct), 4)

            print(
                f"SYNTH_PROTECTIVE_STATE symbol={symbol} qty={exit_qty} raw_qty={qty} "
                f"avg={avg_price} current={current_price} stop={stop_price} "
                f"armed={int(armed)} dry_run={int(live_dry_run)}",
                flush=True,
            )

            if current_price > stop_price and not force_trigger:
                print(f"SYNTH_PROTECTIVE_HOLD symbol={symbol}")
                return 0

            if force_trigger:
                print(
                    f"SYNTH_PROTECTIVE_FORCE_TRIGGER_ACTIVE "
                    f"symbol={symbol} current={current_price} stop={stop_price}",
                    flush=True,
                )

            if not armed:
                print(f"SYNTH_PROTECTIVE_TRIGGER_NOT_ARMED symbol={symbol}")
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
                print(f"SYNTH_PROTECTIVE_ALREADY_ACTIVE symbol={symbol} active={active}")
                return 0

            mode = "shadow" if live_dry_run else "real"
            reason = "synthetic_protective_shadow_sell" if live_dry_run else "synthetic_protective_real_sell"

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
                    1, %s,
                    %s,
                    jsonb_build_object(
                        'order_type','market',
                        'synthetic_protective',true,
                        'stop_price',%s,
                        'current_price',%s,
                        'avg_price',%s,
                        'stop_pct',%s,
                        'raw_qty',%s
                    )
                )
            """, (
                symbol,
                exit_qty,
                exit_qty,
                mode,
                reason,
                stop_price,
                current_price,
                avg_price,
                stop_pct,
                qty,
            ))

            created = 1
            print(
                f"SYNTH_PROTECTIVE_INTENT_CREATED symbol={symbol} qty={exit_qty} "
                f"raw_qty={qty} mode={mode} reason={reason}",
                flush=True,
            )

    print(f"SYNTHETIC_PROTECTIVE_TRIGGER_OK created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
