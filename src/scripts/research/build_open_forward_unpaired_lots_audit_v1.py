#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal
from collections import deque

import psycopg2
import psycopg2.extras


TARGETS = [
    ("BRM6@RTSX", "BR_CONSERVATIVE_BREAKOUT", "M5"),
    ("BRN6@RTSX", "BR_CONSERVATIVE_BREAKOUT", "M5"),
    ("USDRUBF@RTSX", "USD_INTRADAY_REGIME", "M5"),
]


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def load_fills(cur, symbol: str, strategy: str, timeframe: str) -> list[dict]:
    cur.execute(
        """
        select
            id,
            created_at,
            side,
            qty,
            price,
            origin,
            trade_source
        from trades
        where symbol=%s
          and strategy=%s
          and timeframe=%s
          and coalesce(trade_source,'')='paper'
          and coalesce(origin,'paper')='paper'
          and coalesce(is_invalid,false)=false
        order by created_at, id;
        """,
        (symbol, strategy, timeframe),
    )
    return list(cur.fetchall())


def load_chained_trade_ids(cur, symbol: str, strategy: str, timeframe: str) -> set[int]:
    cur.execute(
        """
        select entry_trade_id as trade_id
        from closed_trade_chains_v3
        where symbol=%s
          and strategy=%s
          and timeframe=%s
          and trade_source='paper'
          and entry_trade_id is not null

        union

        select exit_trade_id as trade_id
        from closed_trade_chains_v3
        where symbol=%s
          and strategy=%s
          and timeframe=%s
          and trade_source='paper'
          and exit_trade_id is not null;
        """,
        (symbol, strategy, timeframe, symbol, strategy, timeframe),
    )
    return {int(r["trade_id"]) for r in cur.fetchall()}


def fifo_unpaired(fills: list[dict]) -> tuple[list[dict], list[dict]]:
    long_q: deque[dict] = deque()
    short_q: deque[dict] = deque()
    pairs: list[dict] = []

    for f in fills:
        side = str(f["side"])
        qty = dec(f["qty"])
        if qty <= 0:
            continue

        current = dict(f)
        current["open_qty"] = qty

        if side == "BUY":
            while qty > 0 and short_q:
                s = short_q[0]
                matched = min(qty, s["open_qty"])
                pairs.append(
                    {
                        "entry_id": s["id"],
                        "exit_id": current["id"],
                        "side": "SELL",
                        "qty": matched,
                    }
                )
                qty -= matched
                s["open_qty"] -= matched
                if s["open_qty"] <= 0:
                    short_q.popleft()

            if qty > 0:
                current["open_qty"] = qty
                long_q.append(current)

        elif side == "SELL":
            while qty > 0 and long_q:
                b = long_q[0]
                matched = min(qty, b["open_qty"])
                pairs.append(
                    {
                        "entry_id": b["id"],
                        "exit_id": current["id"],
                        "side": "BUY",
                        "qty": matched,
                    }
                )
                qty -= matched
                b["open_qty"] -= matched
                if b["open_qty"] <= 0:
                    long_q.popleft()

            if qty > 0:
                current["open_qty"] = qty
                short_q.append(current)

    unpaired = list(long_q) + list(short_q)
    return pairs, unpaired


def main() -> int:
    print("=== OPEN FORWARD UNPAIRED LOTS AUDIT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            total_unpaired = 0
            total_unpaired_chained = 0

            for symbol, strategy, timeframe in TARGETS:
                fills = load_fills(cur, symbol, strategy, timeframe)
                chained_ids = load_chained_trade_ids(cur, symbol, strategy, timeframe)
                pairs, unpaired = fifo_unpaired(fills)

                net_qty = sum(
                    dec(f["qty"]) if f["side"] == "BUY" else -dec(f["qty"])
                    for f in fills
                )

                print()
                print(
                    "TARGET_SUMMARY "
                    f"symbol={symbol} "
                    f"strategy={strategy} "
                    f"timeframe={timeframe} "
                    f"fills={len(fills)} "
                    f"fifo_pairs={len(pairs)} "
                    f"unpaired_lots={len(unpaired)} "
                    f"net_qty={net_qty}"
                )

                for u in unpaired[:30]:
                    is_chained = int(int(u["id"]) in chained_ids)
                    total_unpaired += 1
                    total_unpaired_chained += is_chained

                    print(
                        "UNPAIRED_LOT "
                        f"symbol={symbol} "
                        f"strategy={strategy} "
                        f"timeframe={timeframe} "
                        f"id={u['id']} "
                        f"created_at={u['created_at']} "
                        f"side={u['side']} "
                        f"open_qty={u['open_qty']} "
                        f"price={u['price']} "
                        f"in_closed_chains={is_chained}"
                    )

                if len(unpaired) > 30:
                    print(
                        "UNPAIRED_LOT_TRUNCATED "
                        f"symbol={symbol} "
                        f"hidden={len(unpaired) - 30}"
                    )

    print()
    print(
        "UNPAIRED_TOTALS "
        f"unpaired_lots={total_unpaired} "
        f"unpaired_already_in_chains={total_unpaired_chained}"
    )

    if total_unpaired_chained > 0:
        verdict = "CHAINED_TRADES_STILL_UNPAIRED_REVIEW_PAIRING_LOGIC"
    elif total_unpaired > 0:
        verdict = "UNPAIRED_LOTS_CONFIRMED"
    else:
        verdict = "NO_UNPAIRED_LOTS"

    print(f"VERDICT={verdict}")
    print("OPEN_FORWARD_UNPAIRED_LOTS_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
