#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2
import psycopg2.extras

from finam_core.signals.intent_semantics_v2 import classify_intent_semantics_v2


DEFAULT_SYMBOLS = [
    "BRN6@RTSX",
    "BRM6@RTSX",
    "NGN6@RTSX",
    "USDRUBF@RTSX",
    "SBERP@MISX",
    "PLZL@MISX",
    "LKOH@MISX",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    p.add_argument("--trade-source", default="paper")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    dsn = os.environ["DATABASE_URL"]
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    print("=== MULTI SYMBOL INTENT SEMANTICS SHADOW REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(symbols)}")
    print(f"trade_source={args.trade_source}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                select
                    id,
                    symbol,
                    side,
                    qty,
                    price,
                    ts,
                    coalesce(strategy, 'UNKNOWN') as strategy,
                    coalesce(timeframe, 'UNKNOWN') as timeframe,
                    coalesce(origin, 'UNKNOWN') as origin,
                    coalesce(trade_source, 'UNKNOWN') as trade_source
                from trades
                where symbol = any(%s)
                  and trade_source = %s
                  and coalesce(is_invalid,false)=false
                order by symbol, ts, id;
                """,
                (symbols, args.trade_source),
            )
            rows = cur.fetchall()

    positions: dict[str, float] = {}
    by_symbol_action: dict[tuple[str, str], int] = {}
    by_symbol_side_action: dict[tuple[str, str, str], int] = {}
    by_strategy_action: dict[tuple[str, str], int] = {}
    by_symbol_final: dict[str, float] = {}

    reduce_only_total = 0
    opens_total = 0
    short_action_total = 0
    crosses_zero_total = 0

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

        action = d.action.value
        positions[symbol] = float(d.resulting_position)
        by_symbol_final[symbol] = float(d.resulting_position)

        by_symbol_action[(symbol, action)] = by_symbol_action.get((symbol, action), 0) + 1
        by_symbol_side_action[(symbol, side, action)] = (
            by_symbol_side_action.get((symbol, side, action), 0) + 1
        )

        strategy = str(r["strategy"] or "UNKNOWN")
        by_strategy_action[(strategy, action)] = by_strategy_action.get((strategy, action), 0) + 1

        reduce_only_total += int(d.reduce_only)
        opens_total += int(d.opens_position)
        crosses_zero_total += int(d.crosses_zero)

        if action in {"OPEN_SHORT", "ADD_SHORT", "REDUCE_SHORT", "CLOSE_SHORT"}:
            short_action_total += 1

    print("SUMMARY")
    print(f"ROWS={len(rows)}")
    print(f"REDUCE_ONLY_ROWS={reduce_only_total}")
    print(f"OPENS_POSITION_ROWS={opens_total}")
    print(f"SHORT_ACTION_ROWS={short_action_total}")
    print(f"CROSSES_ZERO_ROWS={crosses_zero_total}")
    print()

    print("FINAL_POSITIONS")
    for symbol in sorted(symbols):
        print(f"FINAL_POSITION_ROW symbol={symbol} final_position={by_symbol_final.get(symbol, 0.0)}")
    print()

    print("ACTION_BY_SYMBOL")
    for (symbol, action), count in sorted(by_symbol_action.items()):
        print(f"SYMBOL_ACTION_ROW symbol={symbol} action={action} rows={count}")
    print()

    print("ACTION_BY_SYMBOL_SIDE")
    for (symbol, side, action), count in sorted(by_symbol_side_action.items()):
        print(f"SYMBOL_SIDE_ACTION_ROW symbol={symbol} side={side} action={action} rows={count}")
    print()

    print("ACTION_BY_STRATEGY")
    for (strategy, action), count in sorted(by_strategy_action.items()):
        print(f"STRATEGY_ACTION_ROW strategy={strategy} action={action} rows={count}")
    print()

    print("SHORT_CAPABILITY_BY_SYMBOL")
    for symbol in sorted(symbols):
        open_short = by_symbol_action.get((symbol, "OPEN_SHORT"), 0)
        add_short = by_symbol_action.get((symbol, "ADD_SHORT"), 0)
        reduce_short = by_symbol_action.get((symbol, "REDUCE_SHORT"), 0)
        close_short = by_symbol_action.get((symbol, "CLOSE_SHORT"), 0)
        short_rows = open_short + add_short + reduce_short + close_short

        if open_short or add_short:
            status = "SHORT_PRESENT"
        elif short_rows:
            status = "SHORT_REDUCTION_ONLY"
        else:
            status = "SHORT_ABSENT"

        print(
            f"SHORT_CAPABILITY_ROW symbol={symbol} "
            f"open_short={open_short} add_short={add_short} "
            f"reduce_short={reduce_short} close_short={close_short} "
            f"status={status}"
        )

    print()
    if short_action_total > 0:
        print("VERDICT=SHORT_SEMANTICS_FOUND_IN_MULTI_SYMBOL_FLOW")
    else:
        print("VERDICT=SHORT_SEMANTICS_ABSENT_IN_MULTI_SYMBOL_FLOW")


if __name__ == "__main__":
    main()
