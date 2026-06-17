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


def main() -> int:
    print("=== OPEN FORWARD CHAIN QTY RECONCILIATION V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    suspicious = 0
    true_unpaired = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol, strategy, timeframe in TARGETS:
                print()
                print(
                    "TARGET "
                    f"symbol={symbol} "
                    f"strategy={strategy} "
                    f"timeframe={timeframe}"
                )

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
                        id,
                        entry_trade_id,
                        exit_trade_id,
                        side,
                        qty,
                        entry_price,
                        exit_price,
                        net_pnl,
                        quality_status,
                        quality_reason
                    from closed_trade_chains_v3
                    where symbol=%s
                      and strategy=%s
                      and timeframe=%s
                      and trade_source='paper'
                    order by entry_ts, exit_ts, id;
                    """,
                    (symbol, strategy, timeframe),
                )
                chains = list(cur.fetchall())

                entry_used = defaultdict(Decimal)
                exit_used = defaultdict(Decimal)

                for c in chains:
                    q = dec(c["qty"])
                    if c["entry_trade_id"] is not None:
                        entry_used[int(c["entry_trade_id"])] += q
                    if c["exit_trade_id"] is not None:
                        exit_used[int(c["exit_trade_id"])] += q

                for f in fills:
                    trade_id = int(f["id"])
                    qty = dec(f["qty"])
                    used_as_entry = entry_used[trade_id]
                    used_as_exit = exit_used[trade_id]

                    if f["side"] == "BUY":
                        chain_used_qty = used_as_entry + used_as_exit
                    elif f["side"] == "SELL":
                        chain_used_qty = used_as_entry + used_as_exit
                    else:
                        chain_used_qty = Decimal("0")

                    chain_remaining = qty - chain_used_qty

                    if chain_remaining > Decimal("0.0000001"):
                        in_chain = int(chain_used_qty > 0)
                        if in_chain:
                            suspicious += 1
                            status = "PARTIALLY_CHAINED_REMAINDER"
                        else:
                            true_unpaired += 1
                            status = "TRUE_UNPAIRED_FILL"

                        print(
                            "QTY_RECON_ROW "
                            f"symbol={symbol} "
                            f"strategy={strategy} "
                            f"timeframe={timeframe} "
                            f"id={trade_id} "
                            f"created_at={f['created_at']} "
                            f"side={f['side']} "
                            f"qty={qty} "
                            f"used_as_entry={used_as_entry} "
                            f"used_as_exit={used_as_exit} "
                            f"chain_used_qty={chain_used_qty} "
                            f"chain_remaining={chain_remaining} "
                            f"price={f['price']} "
                            f"status={status}"
                        )

                print(
                    "TARGET_CHAIN_SUMMARY "
                    f"symbol={symbol} "
                    f"fills={len(fills)} "
                    f"chains={len(chains)} "
                    f"entry_ids_used={len(entry_used)} "
                    f"exit_ids_used={len(exit_used)}"
                )

    print()
    print(
        "QTY_RECON_TOTALS "
        f"partially_chained_remainders={suspicious} "
        f"true_unpaired_fills={true_unpaired}"
    )

    if suspicious > 0:
        verdict = "PARTIAL_CHAIN_REMAINDERS_REQUIRE_DECISION"
    elif true_unpaired > 0:
        verdict = "TRUE_UNPAIRED_FILLS_CONFIRMED"
    else:
        verdict = "NO_CHAIN_QTY_REMAINDERS"

    print(f"VERDICT={verdict}")
    print("OPEN_FORWARD_CHAIN_QTY_RECONCILIATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
