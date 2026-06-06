#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from finam_core.signals.position_action import classify_position_action


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR POSITION ACTION SHADOW AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    id,
                    symbol,
                    side,
                    qty,
                    price,
                    ts,
                    strategy,
                    timeframe,
                    origin,
                    trade_source
                from trades
                where symbol in ('BRM6@RTSX','BRN6@RTSX')
                  and trade_source='paper'
                  and coalesce(is_invalid,false)=false
                order by symbol, ts, id;
            """)
            rows = cur.fetchall()

    positions: dict[str, float] = {}
    counters: dict[tuple[str, str], int] = {}
    by_symbol_action: dict[tuple[str, str], int] = {}
    by_strategy_action: dict[tuple[str, str], int] = {}
    samples = []

    for r in rows:
        symbol = str(r["symbol"])
        side = str(r["side"])
        qty = float(r["qty"] or 0.0)
        pos_before = float(positions.get(symbol, 0.0))

        decision = classify_position_action(
            side=side,
            current_position=pos_before,
            quantity=qty,
        )

        action = decision.action.value
        positions[symbol] = float(decision.resulting_position)

        counters[(side, action)] = counters.get((side, action), 0) + 1
        by_symbol_action[(symbol, action)] = by_symbol_action.get((symbol, action), 0) + 1
        by_strategy_action[(str(r["strategy"] or "UNKNOWN"), action)] = (
            by_strategy_action.get((str(r["strategy"] or "UNKNOWN"), action), 0) + 1
        )

        if len(samples) < 80:
            samples.append((r, pos_before, decision))

    print("SUMMARY")
    print(f"TRADES={len(rows)}")
    for symbol, pos in sorted(positions.items()):
        print(f"FINAL_POSITION_ROW symbol={symbol} final_position={pos}")
    print()

    print("ACTION_BY_SIDE")
    for (side, action), rows_count in sorted(counters.items()):
        print(f"ACTION_SIDE_ROW side={side} action={action} rows={rows_count}")
    print()

    print("ACTION_BY_SYMBOL")
    for (symbol, action), rows_count in sorted(by_symbol_action.items()):
        print(f"ACTION_SYMBOL_ROW symbol={symbol} action={action} rows={rows_count}")
    print()

    print("ACTION_BY_STRATEGY")
    for (strategy, action), rows_count in sorted(by_strategy_action.items()):
        print(f"ACTION_STRATEGY_ROW strategy={strategy} action={action} rows={rows_count}")
    print()

    print("SAMPLE")
    for r, pos_before, decision in samples:
        print(
            "ACTION_SAMPLE_ROW "
            f"id={r['id']} ts={r['ts']} symbol={r['symbol']} side={r['side']} "
            f"qty={r['qty']} price={r['price']} strategy={r['strategy']} "
            f"origin={r['origin']} position_before={pos_before} "
            f"action={decision.action.value} "
            f"position_after={decision.resulting_position} "
            f"crosses_zero={int(decision.crosses_zero)}"
        )
    print()

    open_short = sum(v for (side, action), v in counters.items() if action == "OPEN_SHORT")
    add_short = sum(v for (side, action), v in counters.items() if action == "ADD_SHORT")
    close_short = sum(v for (side, action), v in counters.items() if action == "CLOSE_SHORT")
    reduce_short = sum(v for (side, action), v in counters.items() if action == "REDUCE_SHORT")

    print("SHORT_ACTION_SUMMARY")
    print(
        f"OPEN_SHORT={open_short} ADD_SHORT={add_short} "
        f"REDUCE_SHORT={reduce_short} CLOSE_SHORT={close_short}"
    )

    if open_short > 0 or add_short > 0:
        print("VERDICT=BR_SHORT_ACTION_EXISTS")
    else:
        print("VERDICT=BR_SHORT_ACTION_ABSENT")


if __name__ == "__main__":
    main()
