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

    print("=== MULTI SYMBOL SHORT SANITY AUDIT V1 ===")
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
                    id, symbol, side, qty, price, ts,
                    coalesce(strategy, 'UNKNOWN') as strategy,
                    coalesce(timeframe, 'UNKNOWN') as timeframe,
                    coalesce(origin, 'UNKNOWN') as origin,
                    coalesce(trade_source, 'UNKNOWN') as trade_source,
                    payload
                from trades
                where symbol = any(%s)
                  and trade_source = %s
                  and coalesce(is_invalid,false)=false
                order by symbol, ts, id;
                """,
                (symbols, args.trade_source),
            )
            rows = cur.fetchall()

    positions = {}
    short_rows = []

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

        if d.action.value in {"OPEN_SHORT", "ADD_SHORT", "REDUCE_SHORT", "CLOSE_SHORT"}:
            payload = dict(r["payload"] or {})
            short_rows.append({
                "id": r["id"],
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": r["price"],
                "ts": r["ts"],
                "strategy": str(r["strategy"] or "UNKNOWN"),
                "timeframe": str(r["timeframe"] or "UNKNOWN"),
                "origin": str(r["origin"] or "UNKNOWN"),
                "trade_source": str(r["trade_source"] or "UNKNOWN"),
                "source": str(payload.get("source") or "UNKNOWN"),
                "execution_type": str(payload.get("execution_type") or "UNKNOWN"),
                "reason": str(payload.get("reason") or "UNKNOWN"),
                "position_before": pos_before,
                "position_after": float(d.resulting_position),
                "action": d.action.value,
            })

    print("SUMMARY")
    print(f"TOTAL_ROWS={len(rows)}")
    print(f"SHORT_SEMANTIC_ROWS={len(short_rows)}")
    for symbol in sorted(symbols):
        print(f"FINAL_POSITION_ROW symbol={symbol} final_position={positions.get(symbol, 0.0)}")
    print()

    def grouped(title: str, keys: list[str]) -> None:
        print(title)
        counter = {}
        for r in short_rows:
            k = tuple(r[x] for x in keys)
            counter[k] = counter.get(k, 0) + 1
        for k, count in sorted(counter.items()):
            parts = " ".join(f"{keys[i]}={k[i]}" for i in range(len(keys)))
            print(f"GROUP_ROW {parts} rows={count}")
        print()

    grouped("SHORT_BY_SYMBOL", ["symbol"])
    grouped("SHORT_BY_SYMBOL_ACTION", ["symbol", "action"])
    grouped("SHORT_BY_STRATEGY_ACTION", ["strategy", "action"])
    grouped("SHORT_BY_ORIGIN_ACTION", ["origin", "action"])
    grouped("SHORT_BY_PAYLOAD_SOURCE_ACTION", ["source", "action"])
    grouped("SHORT_BY_EXECUTION_TYPE_ACTION", ["execution_type", "action"])
    grouped("SHORT_BY_REASON_ACTION", ["reason", "action"])

    print("SHORT_SAMPLE")
    for r in short_rows[:80]:
        print(
            "SHORT_SAMPLE_ROW "
            f"id={r['id']} ts={r['ts']} symbol={r['symbol']} side={r['side']} "
            f"qty={r['qty']} price={r['price']} strategy={r['strategy']} "
            f"origin={r['origin']} payload_source={r['source']} "
            f"execution_type={r['execution_type']} reason={r['reason']} "
            f"position_before={r['position_before']} action={r['action']} "
            f"position_after={r['position_after']}"
        )
    print()

    real_ng_short = any(
        r["symbol"].startswith("NG")
        and r["strategy"] in {"NG_CONSERVATIVE_BREAKOUT", "NG_CONSERVATIVE_BREAKOUT_M1"}
        and r["action"] in {"OPEN_SHORT", "ADD_SHORT", "CLOSE_SHORT", "REDUCE_SHORT"}
        for r in short_rows
    )
    br_short = any(r["symbol"].startswith("BR") for r in short_rows)
    unknown_dominated = (
        len(short_rows) > 0
        and sum(1 for r in short_rows if r["strategy"] == "UNKNOWN") / len(short_rows) > 0.5
    )

    print("SANITY_FLAGS")
    print(f"REAL_NG_SHORT_FLOW={int(real_ng_short)}")
    print(f"BR_SHORT_FLOW={int(br_short)}")
    print(f"UNKNOWN_DOMINATED_SHORT_FLOW={int(unknown_dominated)}")

    if real_ng_short and not br_short:
        print("VERDICT=SHORT_ENGINE_EXISTS_BUT_BR_SHORT_ABSENT")
    elif br_short:
        print("VERDICT=BR_SHORT_FLOW_FOUND")
    elif unknown_dominated:
        print("VERDICT=SHORT_FLOW_DIRTY_UNKNOWN_DOMINATED")
    else:
        print("VERDICT=SHORT_FLOW_REQUIRES_MANUAL_REVIEW")


if __name__ == "__main__":
    main()
