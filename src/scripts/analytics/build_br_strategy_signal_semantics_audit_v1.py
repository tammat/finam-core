#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from finam_core.signals.intent_semantics_v2 import classify_intent_semantics_v2


SYMBOLS = ["BRM6@RTSX", "BRN6@RTSX"]


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR STRATEGY SIGNAL SEMANTICS AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("goal=compare_BR_strategy_SELL_signal_with_position_action")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                select
                    id, symbol, side, qty, price, ts,
                    coalesce(strategy, 'UNKNOWN') as strategy,
                    coalesce(timeframe, 'UNKNOWN') as timeframe,
                    coalesce(origin, 'UNKNOWN') as origin,
                    coalesce(trade_source, 'UNKNOWN') as trade_source,
                    payload
                from trades
                where symbol = any(%s)
                  and trade_source='paper'
                  and coalesce(is_invalid,false)=false
                order by symbol, ts, id;
                """,
                (SYMBOLS,),
            )
            trades = cur.fetchall()

            cur.execute(
                """
                select
                    id, symbol, side, ts,
                    coalesce(strategy, 'UNKNOWN') as strategy,
                    coalesce(timeframe, 'UNKNOWN') as timeframe,
                    coalesce(status, 'UNKNOWN') as status,
                    payload
                from signals
                where symbol = any(%s)
                  and coalesce(strategy, 'UNKNOWN') in (
                      'BR_CONSERVATIVE_BREAKOUT',
                      'BR_CONSERVATIVE_BREAKOUT_M5',
                      'HISTORICAL_BREAKOUT_V1'
                  )
                order by symbol, ts, id;
                """,
                (SYMBOLS,),
            )
            signals = cur.fetchall()

    positions: dict[str, float] = {}
    trade_action_rows = []

    for r in trades:
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

        trade_action_rows.append({
            "id": r["id"],
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": r["price"],
            "ts": r["ts"],
            "strategy": str(r["strategy"]),
            "origin": str(r["origin"]),
            "position_before": pos_before,
            "position_after": float(d.resulting_position),
            "action": d.action.value,
            "reason": str((r["payload"] or {}).get("reason") or "UNKNOWN"),
        })

    print("TRADE_ACTION_SUMMARY")
    counter = {}
    for r in trade_action_rows:
        key = (r["symbol"], r["side"], r["action"])
        counter[key] = counter.get(key, 0) + 1
    for (symbol, side, action), rows in sorted(counter.items()):
        print(f"TRADE_ACTION_ROW symbol={symbol} side={side} action={action} rows={rows}")
    print()

    print("BR_SELL_TRADE_SEMANTICS")
    sell_rows = [r for r in trade_action_rows if r["side"] == "SELL"]
    open_short = [r for r in sell_rows if r["action"] == "OPEN_SHORT"]
    add_short = [r for r in sell_rows if r["action"] == "ADD_SHORT"]
    reduce_long = [r for r in sell_rows if r["action"] == "REDUCE_LONG"]
    close_long = [r for r in sell_rows if r["action"] == "CLOSE_LONG"]

    print(f"SELL_ROWS={len(sell_rows)}")
    print(f"SELL_OPEN_SHORT={len(open_short)}")
    print(f"SELL_ADD_SHORT={len(add_short)}")
    print(f"SELL_REDUCE_LONG={len(reduce_long)}")
    print(f"SELL_CLOSE_LONG={len(close_long)}")
    print()

    print("SIGNAL_LAYER_SUMMARY")
    sig_counter = {}
    sell_signal_reasons = {}
    for s in signals:
        payload = dict(s["payload"] or {})
        reason = str(payload.get("reason") or payload.get("signal_reason") or "UNKNOWN")
        key = (str(s["symbol"]), str(s["strategy"]), str(s["side"]), str(s["status"]))
        sig_counter[key] = sig_counter.get(key, 0) + 1
        if str(s["side"]).upper() == "SELL":
            sell_signal_reasons[reason] = sell_signal_reasons.get(reason, 0) + 1

    for (symbol, strategy, side, status), rows in sorted(sig_counter.items()):
        print(
            f"SIGNAL_ROW symbol={symbol} strategy={strategy} "
            f"side={side} status={status} rows={rows}"
        )
    print()

    print("SELL_SIGNAL_REASONS")
    for reason, rows in sorted(sell_signal_reasons.items()):
        print(f"SELL_SIGNAL_REASON_ROW reason={reason} rows={rows}")
    print()

    print("SELL_TRADE_SAMPLE")
    for r in sell_rows[:80]:
        print(
            "SELL_TRADE_ROW "
            f"id={r['id']} ts={r['ts']} symbol={r['symbol']} side={r['side']} "
            f"qty={r['qty']} price={r['price']} strategy={r['strategy']} "
            f"origin={r['origin']} position_before={r['position_before']} "
            f"action={r['action']} position_after={r['position_after']} "
            f"reason={r['reason']}"
        )
    print()

    print("FINAL_POSITIONS")
    for symbol in SYMBOLS:
        print(f"FINAL_POSITION_ROW symbol={symbol} final_position={positions.get(symbol, 0.0)}")
    print()

    if len(sell_rows) > 0 and len(open_short) == 0 and len(add_short) == 0:
        print("VERDICT=BR_SELL_SIGNALS_EXIST_BUT_ONLY_REDUCE_OR_CLOSE_LONG")
    elif len(open_short) > 0 or len(add_short) > 0:
        print("VERDICT=BR_SHORT_SEMANTICS_ALREADY_EXISTS")
    else:
        print("VERDICT=BR_SELL_SIGNAL_ABSENT_OR_UNCLEAR")


if __name__ == "__main__":
    main()
