#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from finam_core.signals.intent_semantics_v2 import classify_intent_semantics_v2


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR INTENT SEMANTICS V2 SHADOW REPORT ===")
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
    by_action: dict[str, int] = {}
    by_side_action: dict[tuple[str, str], int] = {}
    by_symbol_action: dict[tuple[str, str], int] = {}
    by_strategy_action: dict[tuple[str, str], int] = {}

    reduce_only_rows = 0
    opens_rows = 0
    crosses_zero_rows = 0

    samples = []

    for r in rows:
        symbol = str(r["symbol"])
        side = str(r["side"])
        qty = float(r["qty"] or 0.0)
        pos_before = float(positions.get(symbol, 0.0))

        d = classify_intent_semantics_v2(
            side=side,
            current_position=pos_before,
            requested_qty=qty,
        )

        positions[symbol] = float(d.resulting_position)

        action = d.action.value
        by_action[action] = by_action.get(action, 0) + 1
        by_side_action[(side, action)] = by_side_action.get((side, action), 0) + 1
        by_symbol_action[(symbol, action)] = by_symbol_action.get((symbol, action), 0) + 1

        strategy = str(r["strategy"] or "UNKNOWN")
        by_strategy_action[(strategy, action)] = by_strategy_action.get((strategy, action), 0) + 1

        reduce_only_rows += int(d.reduce_only)
        opens_rows += int(d.opens_position)
        crosses_zero_rows += int(d.crosses_zero)

        if len(samples) < 80:
            samples.append((r, pos_before, d))

    print("SUMMARY")
    print(f"ROWS={len(rows)}")
    print(f"REDUCE_ONLY_ROWS={reduce_only_rows}")
    print(f"OPENS_POSITION_ROWS={opens_rows}")
    print(f"CROSSES_ZERO_ROWS={crosses_zero_rows}")
    for symbol, pos in sorted(positions.items()):
        print(f"FINAL_POSITION_ROW symbol={symbol} final_position={pos}")
    print()

    print("ACTION_SUMMARY")
    for action, count in sorted(by_action.items()):
        print(f"ACTION_ROW action={action} rows={count}")
    print()

    print("ACTION_BY_SIDE")
    for (side, action), count in sorted(by_side_action.items()):
        print(f"SIDE_ACTION_ROW side={side} action={action} rows={count}")
    print()

    print("ACTION_BY_SYMBOL")
    for (symbol, action), count in sorted(by_symbol_action.items()):
        print(f"SYMBOL_ACTION_ROW symbol={symbol} action={action} rows={count}")
    print()

    print("ACTION_BY_STRATEGY")
    for (strategy, action), count in sorted(by_strategy_action.items()):
        print(f"STRATEGY_ACTION_ROW strategy={strategy} action={action} rows={count}")
    print()

    print("SAMPLE_ROWS")
    for r, pos_before, d in samples:
        print(
            "SEMANTICS_SAMPLE_ROW "
            f"id={r['id']} ts={r['ts']} symbol={r['symbol']} side={r['side']} "
            f"qty={r['qty']} price={r['price']} strategy={r['strategy']} "
            f"origin={r['origin']} position_before={pos_before} "
            f"action={d.action.value} reduce_only={int(d.reduce_only)} "
            f"opens={int(d.opens_position)} closes={int(d.closes_position)} "
            f"reduces={int(d.reduces_position)} adds={int(d.adds_position)} "
            f"position_after={d.resulting_position} crosses_zero={int(d.crosses_zero)}"
        )
    print()

    open_short = by_action.get("OPEN_SHORT", 0)
    add_short = by_action.get("ADD_SHORT", 0)
    reduce_short = by_action.get("REDUCE_SHORT", 0)
    close_short = by_action.get("CLOSE_SHORT", 0)

    print("SHORT_SEMANTICS_SUMMARY")
    print(
        f"OPEN_SHORT={open_short} ADD_SHORT={add_short} "
        f"REDUCE_SHORT={reduce_short} CLOSE_SHORT={close_short}"
    )

    if open_short > 0 or add_short > 0:
        print("VERDICT=BR_SHORT_SEMANTICS_PRESENT")
    else:
        print("VERDICT=BR_SHORT_SEMANTICS_ABSENT")


if __name__ == "__main__":
    main()
