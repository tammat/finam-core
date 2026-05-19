from __future__ import annotations

import json
import os

import psycopg2

from finam_core.portfolio.position_lifecycle_manager import PositionLifecycleManager


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)
    manager = PositionLifecycleManager()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    p.symbol,
                    p.qty,
                    p.avg_price,
                    p.current_price
                from real_portfolio_positions p
                where coalesce(p.qty, 0) > 0
                order by p.updated_at desc
                limit 50
            """)

            positions = cur.fetchall()
            processed = 0
            actions = 0

            for symbol, qty, avg_price, current_price in positions:
                cur.execute("""
                    select
                        entry_price,
                        stop_loss,
                        take_profit,
                        raw_json
                    from radar_candidate_analysis
                    where symbol = %s
                      and source = 'watch_candidate_runtime_analyzer'
                      and decision = 'ALERT'
                    order by created_at desc
                    limit 1
                """, (symbol,))

                setup = cur.fetchone()
                if setup is None:
                    continue

                entry_price, stop_loss, take_profit, raw_json = setup

                if not entry_price or not stop_loss or not take_profit:
                    continue

                cur.execute("""
                    insert into position_lifecycle_state (
                        symbol,
                        strategy,
                        entry_price,
                        initial_qty,
                        remaining_qty,
                        current_stop,
                        current_take_profit,
                        raw
                    )
                    values (%s,'default',%s,%s,%s,%s,%s,%s::jsonb)
                    on conflict(symbol, strategy) do update set
                        remaining_qty = excluded.remaining_qty,
                        current_take_profit = excluded.current_take_profit,
                        updated_at = now()
                    returning
                        current_stop,
                        coalesce(profit_lock_done, false),
                        raw
                """, (
                    symbol,
                    entry_price,
                    qty,
                    qty,
                    stop_loss,
                    take_profit,
                    json.dumps({
                        "source": "position_lifecycle_manager",
                        "setup": raw_json or {},
                    }, ensure_ascii=False, default=str),
                ))

                state_row = cur.fetchone()
                current_stop, breakeven_done, lifecycle_raw = state_row

                decision = manager.evaluate(
                    side="BUY",
                    entry_price=float(entry_price),
                    current_price=float(current_price),
                    current_stop=float(current_stop or stop_loss),
                    take_profit=float(take_profit),
                    breakeven_done=bool(breakeven_done),
                )

                processed += 1

                if decision.action == "MOVE_STOP":
                    cur.execute("""
                        update position_lifecycle_state
                        set
                            current_stop = %s,
                            profit_lock_done = true,
                            updated_at = now(),
                            raw = coalesce(raw, '{}'::jsonb) || %s::jsonb
                        where symbol = %s
                          and strategy = 'default'
                    """, (
                        decision.new_stop,
                        json.dumps({
                            "last_action": decision.action,
                            "last_reason": decision.reason,
                        }, ensure_ascii=False),
                        symbol,
                    ))
                    actions += 1

                elif decision.action == "CLOSE":
                    cur.execute("""
                        update position_lifecycle_state
                        set
                            remaining_qty = 0,
                            updated_at = now(),
                            raw = coalesce(raw, '{}'::jsonb) || %s::jsonb
                        where symbol = %s
                          and strategy = 'default'
                    """, (
                        json.dumps({
                            "last_action": decision.action,
                            "last_reason": decision.reason,
                        }, ensure_ascii=False),
                        symbol,
                    ))
                    actions += 1

                print(
                    "POSITION_LIFECYCLE_DECISION "
                    f"symbol={symbol} "
                    f"action={decision.action} "
                    f"stop={decision.new_stop:.4f} "
                    f"reason={decision.reason}",
                    flush=True,
                )

    print(
        f"POSITION_LIFECYCLE_MANAGER_OK processed={processed} actions={actions}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
