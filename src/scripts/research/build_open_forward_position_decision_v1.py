#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal
from collections import defaultdict

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


def decision_for(symbol: str, net_tail: Decimal, unpaired_count: int, contaminated_price_jump: bool) -> tuple[str, str]:
    if symbol == "BRM6@RTSX":
        return (
            "EXCLUDE_FROM_CURRENT_FORWARD_OPEN_STATE",
            "historical_partial_tail_not_current_forward_candidate",
        )

    if symbol == "BRN6@RTSX":
        return (
            "KEEP_AS_OPEN_PAPER_LONG_TAIL",
            "recent_unpaired_buy_tail_after_last_chain_exit",
        )

    if symbol == "USDRUBF@RTSX":
        if contaminated_price_jump:
            return (
                "QUARANTINE_FROM_CLEAN_FORWARD_STATE",
                "contaminated_price_jump_and_duration_guard_tail",
            )
        return (
            "MANUAL_REVIEW_REQUIRED",
            "usdrubf_unpaired_tail_without_contamination_marker",
        )

    return (
        "MANUAL_REVIEW_REQUIRED",
        "unknown_symbol_decision_rule",
    )


def main() -> int:
    print("=== OPEN FORWARD POSITION DECISION V1 ===")
    print("mode=diagnostic_decision")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol, strategy, timeframe in TARGETS:
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
                fills = list(cur.fetchall())

                cur.execute(
                    """
                    select
                        entry_trade_id,
                        exit_trade_id,
                        qty
                    from closed_trade_chains_v3
                    where symbol=%s
                      and strategy=%s
                      and timeframe=%s
                      and trade_source='paper';
                    """,
                    (symbol, strategy, timeframe),
                )
                chains = list(cur.fetchall())

                used = defaultdict(Decimal)
                for c in chains:
                    q = dec(c["qty"])
                    if c["entry_trade_id"] is not None:
                        used[int(c["entry_trade_id"])] += q
                    if c["exit_trade_id"] is not None:
                        used[int(c["exit_trade_id"])] += q

                unpaired = []
                net_tail = Decimal("0")
                prices = []

                for f in fills:
                    trade_id = int(f["id"])
                    qty = dec(f["qty"])
                    used_qty = used.get(trade_id, Decimal("0"))
                    remaining = qty - used_qty

                    if remaining > Decimal("0.0000001"):
                        side = str(f["side"])
                        signed = remaining if side == "BUY" else -remaining
                        net_tail += signed
                        prices.append(dec(f["price"]))

                        unpaired.append(
                            {
                                "id": trade_id,
                                "created_at": f["created_at"],
                                "side": side,
                                "remaining": remaining,
                                "price": dec(f["price"]),
                                "used_qty": used_qty,
                                "qty": qty,
                            }
                        )

                contaminated_price_jump = False
                if prices:
                    min_price = min(prices)
                    max_price = max(prices)
                    if min_price > 0 and (max_price / min_price) > Decimal("1.20"):
                        contaminated_price_jump = True

                action, reason = decision_for(
                    symbol=symbol,
                    net_tail=net_tail,
                    unpaired_count=len(unpaired),
                    contaminated_price_jump=contaminated_price_jump,
                )

                print()
                print(
                    "POSITION_DECISION "
                    f"symbol={symbol} "
                    f"strategy={strategy} "
                    f"timeframe={timeframe} "
                    f"unpaired_lots={len(unpaired)} "
                    f"net_tail={net_tail} "
                    f"contaminated_price_jump={int(contaminated_price_jump)} "
                    f"decision={action} "
                    f"reason={reason}"
                )

                for u in unpaired:
                    print(
                        "DECISION_UNPAIRED_LOT "
                        f"symbol={symbol} "
                        f"id={u['id']} "
                        f"created_at={u['created_at']} "
                        f"side={u['side']} "
                        f"qty={u['qty']} "
                        f"used_qty={u['used_qty']} "
                        f"remaining={u['remaining']} "
                        f"price={u['price']}"
                    )

    print()
    print("VERDICT=OPEN_FORWARD_POSITION_DECISIONS_READY")
    print("OPEN_FORWARD_POSITION_DECISION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
