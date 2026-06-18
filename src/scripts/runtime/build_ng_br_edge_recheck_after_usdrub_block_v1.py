#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# NG_BR_EDGE_RECHECK_AFTER_USDRUB_BLOCK_V1
# Read-only пересчёт edge только по BR/NG после блокировки USDRUB_REGIME.
# Скрипт ничего не меняет в БД, runtime, execution и real trading.


TARGET_SYMBOLS = ("NGM6@RTSX", "NGN6@RTSX", "BRN6@RTSX")


TRADES_SQL = """
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    continuous_symbol,
    side,
    qty,
    price,
    commission
from trades
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
  and symbol = any(%s)
  and coalesce(strategy, '') <> ''
  and coalesce(timeframe, '') <> ''
order by created_at asc, id asc;
"""


@dataclass
class Trade:
    id: int
    created_at: Any
    symbol: str
    strategy: str
    timeframe: str
    continuous_symbol: str
    side: str
    qty: float
    price: float
    commission: float


@dataclass
class Cycle:
    symbol: str
    strategy: str
    timeframe: str
    open_time: Any
    close_time: Any
    qty: float
    open_price: float
    close_price: float
    gross_pnl: float
    commission: float
    net_pnl: float
    duration_sec: float


def fnum(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def safe_div(a: float, b: float) -> float | None:
    if abs(b) < 1e-12:
        return None
    return a / b


def load_trades() -> list[Trade]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL, (list(TARGET_SYMBOLS),))
            rows = cur.fetchall()

    return [
        Trade(
            id=int(r["id"]),
            created_at=r["created_at"],
            symbol=str(r["symbol"]),
            strategy=str(r["strategy"]),
            timeframe=str(r["timeframe"]),
            continuous_symbol=str(r.get("continuous_symbol") or ""),
            side=str(r["side"]).upper(),
            qty=fnum(r["qty"]),
            price=fnum(r["price"]),
            commission=fnum(r["commission"]),
        )
        for r in rows
    ]


def reconstruct_cycles(trades: list[Trade]) -> tuple[list[Cycle], dict[tuple[str, str, str], float]]:
    inventory: dict[tuple[str, str, str], deque[Trade]] = defaultdict(deque)
    open_tail: dict[tuple[str, str, str], float] = defaultdict(float)
    cycles: list[Cycle] = []

    for trade in trades:
        key = (trade.symbol, trade.strategy, trade.timeframe)

        if trade.side == "BUY":
            inventory[key].append(trade)
            open_tail[key] += trade.qty
            continue

        if trade.side == "SELL":
            qty_left = trade.qty

            while qty_left > 1e-12 and inventory[key]:
                opened = inventory[key][0]
                q = min(qty_left, opened.qty)

                gross = (trade.price - opened.price) * q
                commission = opened.commission + trade.commission
                net = gross - commission

                try:
                    duration_sec = (trade.created_at - opened.created_at).total_seconds()
                except Exception:
                    duration_sec = 0.0

                cycles.append(
                    Cycle(
                        symbol=trade.symbol,
                        strategy=trade.strategy,
                        timeframe=trade.timeframe,
                        open_time=opened.created_at,
                        close_time=trade.created_at,
                        qty=q,
                        open_price=opened.price,
                        close_price=trade.price,
                        gross_pnl=gross,
                        commission=commission,
                        net_pnl=net,
                        duration_sec=duration_sec,
                    )
                )

                opened.qty -= q
                qty_left -= q
                open_tail[key] -= q

                if opened.qty <= 1e-12:
                    inventory[key].popleft()

            if qty_left > 1e-12:
                open_tail[key] -= qty_left

    return cycles, dict(open_tail)


def classify(
    *,
    trades: int,
    closed_cycles: int,
    gross: float,
    commission: float,
    net: float,
    avg_gross: float,
    avg_commission: float,
    profit_factor: float | None,
) -> tuple[str, str]:
    if closed_cycles < 5:
        return "INSUFFICIENT_DATA", "too_few_closed_cycles"

    if net < 0 and abs(avg_gross) < avg_commission:
        return "FEE_DRAG_DOMINATES", "average_gross_smaller_than_commission"

    if gross < 0:
        return "NEGATIVE_GROSS_EDGE", "gross_negative_before_commission"

    if profit_factor is not None and profit_factor < 1:
        return "NEGATIVE_EXPECTANCY", "profit_factor_below_one"

    if net > 0 and gross > commission:
        return "RESEARCH_CANDIDATE", "positive_after_commission"

    return "REVIEW_REQUIRED", "mixed_metrics"


def main() -> int:
    print("=== NG BR EDGE RECHECK AFTER USDRUB BLOCK V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("symbols=" + ",".join(TARGET_SYMBOLS))
    print()

    trades = load_trades()
    cycles, open_tail = reconstruct_cycles(trades)

    trade_groups: dict[tuple[str, str, str], list[Trade]] = defaultdict(list)
    cycle_groups: dict[tuple[str, str, str], list[Cycle]] = defaultdict(list)

    for t in trades:
        trade_groups[(t.symbol, t.strategy, t.timeframe)].append(t)

    for c in cycles:
        cycle_groups[(c.symbol, c.strategy, c.timeframe)].append(c)

    keys = sorted(set(trade_groups) | set(cycle_groups))

    rows: list[dict[str, Any]] = []

    for key in keys:
        group_trades = trade_groups.get(key, [])
        group_cycles = cycle_groups.get(key, [])

        gross = sum(c.gross_pnl for c in group_cycles)
        commission = sum(c.commission for c in group_cycles)
        net = sum(c.net_pnl for c in group_cycles)
        wins = [c for c in group_cycles if c.net_pnl > 0]
        losses = [c for c in group_cycles if c.net_pnl < 0]

        gross_profit = sum(c.net_pnl for c in wins)
        gross_loss = abs(sum(c.net_pnl for c in losses))
        profit_factor = safe_div(gross_profit, gross_loss)

        closed = len(group_cycles)
        avg_gross = safe_div(gross, closed) or 0.0
        avg_commission = safe_div(commission, closed) or 0.0
        avg_net = safe_div(net, closed) or 0.0
        avg_duration = safe_div(sum(c.duration_sec for c in group_cycles), closed) or 0.0

        verdict, reason = classify(
            trades=len(group_trades),
            closed_cycles=closed,
            gross=gross,
            commission=commission,
            net=net,
            avg_gross=avg_gross,
            avg_commission=avg_commission,
            profit_factor=profit_factor,
        )

        rows.append(
            {
                "symbol": key[0],
                "strategy": key[1],
                "timeframe": key[2],
                "trades": len(group_trades),
                "buy_trades": sum(1 for t in group_trades if t.side == "BUY"),
                "sell_trades": sum(1 for t in group_trades if t.side == "SELL"),
                "closed_cycles": closed,
                "open_tail": open_tail.get(key, 0.0),
                "wins": len(wins),
                "losses": len(losses),
                "winrate": safe_div(len(wins), closed) or 0.0,
                "profit_factor": profit_factor,
                "gross_pnl": gross,
                "commission": commission,
                "net_pnl": net,
                "avg_gross_per_cycle": avg_gross,
                "avg_commission_per_cycle": avg_commission,
                "avg_net_per_cycle": avg_net,
                "avg_duration_sec": avg_duration,
                "required_gross_x3_commission": avg_commission * 3,
                "verdict": verdict,
                "reason": reason,
            }
        )

    rows.sort(key=lambda r: r["net_pnl"])

    print("NG_BR_EDGE_RECHECK_ROWS")
    for r in rows:
        pf = "NULL" if r["profit_factor"] is None else f"{r['profit_factor']:.6f}"
        print(
            "NG_BR_EDGE_RECHECK_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"trades={r['trades']} "
            f"buy_trades={r['buy_trades']} "
            f"sell_trades={r['sell_trades']} "
            f"closed_cycles={r['closed_cycles']} "
            f"open_tail={r['open_tail']:.6f} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"winrate={r['winrate']:.4f} "
            f"profit_factor={pf} "
            f"gross_pnl={r['gross_pnl']:.6f} "
            f"commission={r['commission']:.6f} "
            f"net_pnl={r['net_pnl']:.6f} "
            f"avg_gross_per_cycle={r['avg_gross_per_cycle']:.6f} "
            f"avg_commission_per_cycle={r['avg_commission_per_cycle']:.6f} "
            f"avg_net_per_cycle={r['avg_net_per_cycle']:.6f} "
            f"avg_duration_sec={r['avg_duration_sec']:.2f} "
            f"required_gross_x3_commission={r['required_gross_x3_commission']:.6f} "
            f"verdict={r['verdict']} "
            f"reason={r['reason']}"
        )

    total_trades = sum(r["trades"] for r in rows)
    total_closed = sum(r["closed_cycles"] for r in rows)
    total_gross = sum(r["gross_pnl"] for r in rows)
    total_commission = sum(r["commission"] for r in rows)
    total_net = sum(r["net_pnl"] for r in rows)

    fee_drag_rows = sum(1 for r in rows if r["verdict"] == "FEE_DRAG_DOMINATES")
    candidates = sum(1 for r in rows if r["verdict"] == "RESEARCH_CANDIDATE")
    insufficient = sum(1 for r in rows if r["verdict"] == "INSUFFICIENT_DATA")

    print()
    print("NG_BR_EDGE_RECHECK_SUMMARY")
    print(f"rows={len(rows)}")
    print(f"trades_total={total_trades}")
    print(f"closed_cycles_total={total_closed}")
    print(f"gross_pnl_total={total_gross:.6f}")
    print(f"commission_total={total_commission:.6f}")
    print(f"net_pnl_total={total_net:.6f}")
    print(f"fee_drag_rows={fee_drag_rows}")
    print(f"research_candidates={candidates}")
    print(f"insufficient_data_rows={insufficient}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if candidates > 0:
        print("VERDICT=NG_BR_EDGE_RECHECK_HAS_RESEARCH_CANDIDATE")
    elif fee_drag_rows > 0:
        print("VERDICT=NG_BR_EDGE_RECHECK_FEE_DRAG_DOMINATES")
    elif insufficient == len(rows):
        print("VERDICT=NG_BR_EDGE_RECHECK_INSUFFICIENT_DATA")
    else:
        print("VERDICT=NG_BR_EDGE_RECHECK_NO_CONFIRMED_EDGE")

    print("NG_BR_EDGE_RECHECK_AFTER_USDRUB_BLOCK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
