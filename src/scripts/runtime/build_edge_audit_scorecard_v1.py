#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EDGE_AUDIT_SCORECARD_V1
# Read-only аудит торгового edge.
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
    commission,
    continuous_symbol,
    trade_source,
    origin,
    payload
from trades
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
  and coalesce(strategy, '') <> ''
  and strategy not in ('UNKNOWN', 'UNKNOWN_STRATEGY')
  and coalesce(timeframe, '') <> ''
  and timeframe not in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
order by created_at asc, id asc;
"""


@dataclass
class Trade:
    id: int
    created_at: Any
    symbol: str
    strategy: str
    timeframe: str
    side: str
    qty: float
    price: float
    commission: float
    continuous_symbol: str
    trade_source: str
    origin: str


@dataclass
class Cycle:
    symbol: str
    strategy: str
    timeframe: str
    side_open: str
    side_close: str
    qty: float
    open_time: Any
    close_time: Any
    open_price: float
    close_price: float
    gross_pnl: float
    commission: float
    net_pnl: float
    duration_sec: float


def fnum(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
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

    trades: list[Trade] = []
    for row in rows:
        trades.append(
            Trade(
                id=int(row["id"]),
                created_at=row["created_at"],
                symbol=str(row["symbol"]),
                strategy=str(row["strategy"]),
                timeframe=str(row["timeframe"]),
                side=str(row["side"]).upper(),
                qty=fnum(row["qty"]),
                price=fnum(row["price"]),
                commission=fnum(row["commission"]),
                continuous_symbol=str(row.get("continuous_symbol") or ""),
                trade_source=str(row.get("trade_source") or ""),
                origin=str(row.get("origin") or ""),
            )
        )
    return trades


def reconstruct_long_fifo_cycles(trades: list[Trade]) -> tuple[list[Cycle], dict[tuple[str, str, str], float]]:
    inventory: dict[tuple[str, str, str], deque[Trade]] = defaultdict(deque)
    open_tail: dict[tuple[str, str, str], float] = defaultdict(float)
    cycles: list[Cycle] = []

    for trade in trades:
        key = (trade.symbol, trade.strategy, trade.timeframe)
        qty_left = trade.qty

        if qty_left <= 0:
            continue

        if trade.side in ("BUY", "LONG"):
            inventory[key].append(trade)
            open_tail[key] += qty_left
            continue

        if trade.side in ("SELL", "SHORT"):
            while qty_left > 1e-12 and inventory[key]:
                opened = inventory[key][0]
                matched_qty = min(qty_left, opened.qty)

                gross = (trade.price - opened.price) * matched_qty
                commission = (opened.commission + trade.commission) * (
                    matched_qty / max(trade.qty, 1e-12)
                )
                net = gross - commission

                try:
                    duration = (trade.created_at - opened.created_at).total_seconds()
                except Exception:
                    duration = 0.0

                cycles.append(
                    Cycle(
                        symbol=trade.symbol,
                        strategy=trade.strategy,
                        timeframe=trade.timeframe,
                        side_open="BUY",
                        side_close="SELL",
                        qty=matched_qty,
                        open_time=opened.created_at,
                        close_time=trade.created_at,
                        open_price=opened.price,
                        close_price=trade.price,
                        gross_pnl=gross,
                        commission=commission,
                        net_pnl=net,
                        duration_sec=duration,
                    )
                )

                opened.qty -= matched_qty
                qty_left -= matched_qty
                open_tail[key] -= matched_qty

                if opened.qty <= 1e-12:
                    inventory[key].popleft()

            if qty_left > 1e-12:
                open_tail[key] -= qty_left

    return cycles, dict(open_tail)


def safe_div(a: float, b: float) -> float | None:
    if abs(b) < 1e-12:
        return None
    return a / b


def classify(row: dict[str, Any]) -> tuple[str, str]:
    cycles = int(row["closed_cycles"])
    net = float(row["net_pnl"])
    gross = float(row["gross_pnl"])
    avg_gross = float(row["avg_gross_per_cycle"])
    avg_comm = float(row["avg_commission_per_cycle"])
    avg_duration = float(row["avg_duration_sec"])
    pf = row["profit_factor"]

    if cycles < 5:
        return "INSUFFICIENT_DATA", "too_few_closed_cycles"

    if net < 0 and abs(avg_gross) < avg_comm:
        return "FEE_DRAG_DOMINATES", "average_gross_smaller_than_commission"

    if net < 0 and gross < 0:
        return "NEGATIVE_ENTRY_EXIT_EDGE", "gross_pnl_negative_before_commission"

    if avg_duration < 60 and avg_comm > abs(avg_gross):
        return "MICROSCALP_NO_ECONOMIC_ROOM", "holding_too_short_for_commission"

    if pf is not None and pf < 1:
        return "NEGATIVE_EXPECTANCY", "profit_factor_below_one"

    if net >= 0 and gross > 0:
        return "RESEARCH_CANDIDATE", "positive_net_and_gross"

    return "REVIEW_REQUIRED", "mixed_metrics"


def main() -> int:
    print("=== EDGE AUDIT SCORECARD V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    trades = load_trades()
    cycles, open_tail = reconstruct_long_fifo_cycles(trades)

    grouped: dict[tuple[str, str, str], list[Cycle]] = defaultdict(list)
    trade_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    side_counts: dict[tuple[str, str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for trade in trades:
        key = (trade.symbol, trade.strategy, trade.timeframe)
        trade_counts[key] += 1
        side_counts[key][trade.side] += 1

    for cycle in cycles:
        grouped[(cycle.symbol, cycle.strategy, cycle.timeframe)].append(cycle)

    keys = sorted(set(trade_counts) | set(grouped))

    rows: list[dict[str, Any]] = []

    for key in keys:
        symbol, strategy, timeframe = key
        group = grouped.get(key, [])

        gross = sum(c.gross_pnl for c in group)
        commission = sum(c.commission for c in group)
        net = sum(c.net_pnl for c in group)

        wins = [c for c in group if c.net_pnl > 0]
        losses = [c for c in group if c.net_pnl < 0]

        gross_profit = sum(c.net_pnl for c in wins)
        gross_loss = abs(sum(c.net_pnl for c in losses))
        profit_factor = safe_div(gross_profit, gross_loss)

        closed_cycles = len(group)
        avg_gross = safe_div(gross, closed_cycles) or 0.0
        avg_comm = safe_div(commission, closed_cycles) or 0.0
        avg_net = safe_div(net, closed_cycles) or 0.0
        avg_duration = safe_div(sum(c.duration_sec for c in group), closed_cycles) or 0.0

        min_profitable_gross = avg_comm
        required_move_x3_commission = avg_comm * 3.0

        row = {
            "symbol": symbol,
            "strategy": strategy,
            "timeframe": timeframe,
            "trades": trade_counts.get(key, 0),
            "buy_trades": side_counts[key].get("BUY", 0),
            "sell_trades": side_counts[key].get("SELL", 0),
            "closed_cycles": closed_cycles,
            "open_tail": open_tail.get(key, 0.0),
            "wins": len(wins),
            "losses": len(losses),
            "winrate": safe_div(len(wins), closed_cycles) or 0.0,
            "gross_pnl": gross,
            "commission": commission,
            "net_pnl": net,
            "avg_gross_per_cycle": avg_gross,
            "avg_commission_per_cycle": avg_comm,
            "avg_net_per_cycle": avg_net,
            "avg_duration_sec": avg_duration,
            "profit_factor": profit_factor,
            "min_profitable_gross_per_cycle": min_profitable_gross,
            "required_gross_x3_commission": required_move_x3_commission,
        }

        verdict, reason = classify(row)
        row["verdict"] = verdict
        row["reason"] = reason
        rows.append(row)

    rows.sort(key=lambda r: r["net_pnl"])

    print("EDGE_AUDIT_ROWS")
    for row in rows:
        pf = "NULL" if row["profit_factor"] is None else f"{row['profit_factor']:.6f}"
        print(
            "EDGE_AUDIT_ROW "
            f"symbol={row['symbol']} "
            f"strategy={row['strategy']} "
            f"timeframe={row['timeframe']} "
            f"trades={row['trades']} "
            f"buy_trades={row['buy_trades']} "
            f"sell_trades={row['sell_trades']} "
            f"closed_cycles={row['closed_cycles']} "
            f"open_tail={row['open_tail']:.6f} "
            f"wins={row['wins']} "
            f"losses={row['losses']} "
            f"winrate={row['winrate']:.4f} "
            f"profit_factor={pf} "
            f"gross_pnl={row['gross_pnl']:.6f} "
            f"commission={row['commission']:.6f} "
            f"net_pnl={row['net_pnl']:.6f} "
            f"avg_gross_per_cycle={row['avg_gross_per_cycle']:.6f} "
            f"avg_commission_per_cycle={row['avg_commission_per_cycle']:.6f} "
            f"avg_net_per_cycle={row['avg_net_per_cycle']:.6f} "
            f"avg_duration_sec={row['avg_duration_sec']:.2f} "
            f"min_profitable_gross_per_cycle={row['min_profitable_gross_per_cycle']:.6f} "
            f"required_gross_x3_commission={row['required_gross_x3_commission']:.6f} "
            f"verdict={row['verdict']} "
            f"reason={row['reason']}"
        )

    total_gross = sum(row["gross_pnl"] for row in rows)
    total_commission = sum(row["commission"] for row in rows)
    total_net = sum(row["net_pnl"] for row in rows)
    fee_drag = sum(1 for row in rows if row["verdict"] == "FEE_DRAG_DOMINATES")
    negative_edge = sum(1 for row in rows if row["verdict"] == "NEGATIVE_ENTRY_EXIT_EDGE")
    candidates = sum(1 for row in rows if row["verdict"] == "RESEARCH_CANDIDATE")

    print()
    print("EDGE_AUDIT_SUMMARY")
    print(f"rows={len(rows)}")
    print(f"trades_total={sum(row['trades'] for row in rows)}")
    print(f"closed_cycles_total={sum(row['closed_cycles'] for row in rows)}")
    print(f"gross_pnl_total={total_gross:.6f}")
    print(f"commission_total={total_commission:.6f}")
    print(f"net_pnl_total={total_net:.6f}")
    print(f"fee_drag_rows={fee_drag}")
    print(f"negative_edge_rows={negative_edge}")
    print(f"research_candidates={candidates}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if fee_drag > 0:
        print("VERDICT=EDGE_AUDIT_FEE_DRAG_DOMINATES")
    elif negative_edge > 0:
        print("VERDICT=EDGE_AUDIT_NEGATIVE_ENTRY_EXIT_EDGE")
    elif candidates > 0:
        print("VERDICT=EDGE_AUDIT_HAS_RESEARCH_CANDIDATES")
    else:
        print("VERDICT=EDGE_AUDIT_NO_CONFIRMED_EDGE")

    print("EDGE_AUDIT_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
