#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# USDRUB_REGIME_FEE_DRAG_GUARD_PLAN_V1
# Read-only план ограничений для USDRUB_REGIME.
# Ничего не меняет в БД, runtime, execution и real trading.


TRADES_SQL = """
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    side,
    qty,
    price,
    commission
from trades
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
  and symbol = 'USDRUBF@RTSX'
  and strategy = 'USDRUB_REGIME'
  and timeframe = 'LIVE'
order by created_at asc, id asc;
"""


@dataclass
class Trade:
    id: int
    created_at: Any
    side: str
    qty: float
    price: float
    commission: float


@dataclass
class Cycle:
    open_time: Any
    close_time: Any
    qty: float
    open_price: float
    close_price: float
    gross_pnl: float
    commission: float
    net_pnl: float
    duration_sec: float


def fnum(v: Any) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return 0.0


def load_trades() -> list[Trade]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL)
            rows = cur.fetchall()

    return [
        Trade(
            id=int(r["id"]),
            created_at=r["created_at"],
            side=str(r["side"]).upper(),
            qty=fnum(r["qty"]),
            price=fnum(r["price"]),
            commission=fnum(r["commission"]),
        )
        for r in rows
    ]


def reconstruct_cycles(trades: list[Trade]) -> list[Cycle]:
    inventory: deque[Trade] = deque()
    cycles: list[Cycle] = []

    for trade in trades:
        if trade.side == "BUY":
            inventory.append(trade)
            continue

        if trade.side == "SELL":
            qty_left = trade.qty
            while qty_left > 1e-12 and inventory:
                opened = inventory[0]
                q = min(qty_left, opened.qty)

                gross = (trade.price - opened.price) * q
                commission = opened.commission + trade.commission
                net = gross - commission

                try:
                    duration = (trade.created_at - opened.created_at).total_seconds()
                except Exception:
                    duration = 0.0

                cycles.append(
                    Cycle(
                        open_time=opened.created_at,
                        close_time=trade.created_at,
                        qty=q,
                        open_price=opened.price,
                        close_price=trade.price,
                        gross_pnl=gross,
                        commission=commission,
                        net_pnl=net,
                        duration_sec=duration,
                    )
                )

                opened.qty -= q
                qty_left -= q

                if opened.qty <= 1e-12:
                    inventory.popleft()

    return cycles


def main() -> int:
    print("=== USDRUB REGIME FEE DRAG GUARD PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    trades = load_trades()
    cycles = reconstruct_cycles(trades)

    closed = len(cycles)
    gross = sum(c.gross_pnl for c in cycles)
    commission = sum(c.commission for c in cycles)
    net = sum(c.net_pnl for c in cycles)
    wins = sum(1 for c in cycles if c.net_pnl > 0)
    losses = sum(1 for c in cycles if c.net_pnl < 0)

    avg_gross = gross / closed if closed else 0.0
    avg_commission = commission / closed if closed else 0.0
    avg_net = net / closed if closed else 0.0
    avg_duration = sum(c.duration_sec for c in cycles) / closed if closed else 0.0

    required_gross_x1 = avg_commission
    required_gross_x2 = avg_commission * 2.0
    required_gross_x3 = avg_commission * 3.0

    print("USDRUB_FEE_DRAG_METRICS")
    print(f"trades={len(trades)}")
    print(f"closed_cycles={closed}")
    print(f"wins={wins}")
    print(f"losses={losses}")
    print(f"winrate={(wins / closed if closed else 0.0):.4f}")
    print(f"gross_pnl={gross:.6f}")
    print(f"commission={commission:.6f}")
    print(f"net_pnl={net:.6f}")
    print(f"avg_gross_per_cycle={avg_gross:.6f}")
    print(f"avg_commission_per_cycle={avg_commission:.6f}")
    print(f"avg_net_per_cycle={avg_net:.6f}")
    print(f"avg_duration_sec={avg_duration:.2f}")
    print(f"required_gross_x1_commission={required_gross_x1:.6f}")
    print(f"required_gross_x2_commission={required_gross_x2:.6f}")
    print(f"required_gross_x3_commission={required_gross_x3:.6f}")

    print()
    print("USDRUB_FEE_DRAG_GUARD_RECOMMENDATION")
    print("recommended_action=QUARANTINE_RUNTIME")
    print("recommended_runtime_enabled=0")
    print("recommended_research_only=1")
    print("recommended_max_trades_per_day=5")
    print("recommended_cooldown_after_trade_sec=900")
    print("recommended_min_hold_sec=600")
    print(f"recommended_min_expected_gross_move={required_gross_x3:.6f}")
    print("recommended_entry_mode=IMPULSE_ONLY")
    print("recommended_disable_scalping=1")

    print()
    print("USDRUB_FEE_DRAG_GUARD_PLAN_SUMMARY")
    print("runtime_changes_required=1")
    print("execution_changes_required=0")
    print("db_update=0")

    if closed >= 5 and net < 0 and abs(avg_gross) < avg_commission:
        print("VERDICT=USDRUB_REGIME_QUARANTINE_REQUIRED_FEE_DRAG")
    elif closed < 5:
        print("VERDICT=USDRUB_REGIME_INSUFFICIENT_DATA")
    else:
        print("VERDICT=USDRUB_REGIME_REVIEW_REQUIRED")

    print("USDRUB_REGIME_FEE_DRAG_GUARD_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
