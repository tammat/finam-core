#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_SCORECARD_V1
# Считает edge только по clean runtime/paper слою:
# payload.trade_source_class = RUNTIME_OR_PAPER_CLEAN_ENOUGH.
# Historical replay, legacy synthetic/backfill и review-only строки исключены.


LOOKBACK_DAYS = int(os.getenv("CLEAN_RUNTIME_EDGE_LOOKBACK_DAYS", "30"))
MIN_CYCLES = int(os.getenv("CLEAN_RUNTIME_EDGE_MIN_CYCLES", "5"))

SQL = """
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
    commission,
    payload
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
  and payload->>'trade_source_class' = 'RUNTIME_OR_PAPER_CLEAN_ENOUGH'
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
    signal_class: str
    entry_source: str
    entry_regime: str


@dataclass
class Cycle:
    symbol: str
    strategy: str
    timeframe: str
    continuous_symbol: str
    entry_source: str
    entry_signal_class: str
    entry_regime: str
    exit_signal_class: str
    gross_pnl: float
    commission: float
    net_pnl: float
    duration_sec: float


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def fnum(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def payload_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def load_trades() -> list[Trade]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (interval,))
            rows = list(cur.fetchall())

    trades: list[Trade] = []
    for row in rows:
        payload = payload_dict(row.get("payload"))

        trades.append(
            Trade(
                id=int(row["id"]),
                created_at=row["created_at"],
                symbol=sval(row.get("symbol")),
                strategy=sval(row.get("strategy"), "UNKNOWN_STRATEGY"),
                timeframe=sval(row.get("timeframe"), "UNKNOWN_TIMEFRAME"),
                continuous_symbol=sval(row.get("continuous_symbol"), sval(row.get("symbol"))),
                side=sval(row.get("side")).upper(),
                qty=fnum(row.get("qty")),
                price=fnum(row.get("price")),
                commission=fnum(row.get("commission")),
                signal_class=sval(payload.get("signal_class"), "UNKNOWN_SIGNAL_CLASS"),
                entry_source=sval(payload.get("entry_source_normalized") or payload.get("source"), "UNKNOWN_SOURCE"),
                entry_regime=sval(payload.get("entry_regime_normalized") or payload.get("regime"), "UNKNOWN_REGIME"),
            )
        )

    return trades


def reconstruct_cycles(trades: list[Trade]) -> list[Cycle]:
    inventory: dict[tuple[str, str, str], deque[Trade]] = defaultdict(deque)
    cycles: list[Cycle] = []

    for trade in trades:
        key = (trade.symbol, trade.strategy, trade.timeframe)

        if trade.side == "BUY":
            inventory[key].append(trade)
            continue

        if trade.side != "SELL":
            continue

        qty_left = trade.qty

        while qty_left > 1e-12 and inventory[key]:
            entry = inventory[key][0]
            qty = min(qty_left, entry.qty)

            gross = (trade.price - entry.price) * qty
            commission = entry.commission + trade.commission
            net = gross - commission

            try:
                duration = (trade.created_at - entry.created_at).total_seconds()
            except Exception:
                duration = 0.0

            cycles.append(
                Cycle(
                    symbol=trade.symbol,
                    strategy=trade.strategy,
                    timeframe=trade.timeframe,
                    continuous_symbol=trade.continuous_symbol,
                    entry_source=entry.entry_source,
                    entry_signal_class=entry.signal_class,
                    entry_regime=entry.entry_regime,
                    exit_signal_class=trade.signal_class,
                    gross_pnl=gross,
                    commission=commission,
                    net_pnl=net,
                    duration_sec=duration,
                )
            )

            entry.qty -= qty
            qty_left -= qty

            if entry.qty <= 1e-12:
                inventory[key].popleft()

    return cycles


def safe_div(a: float, b: float) -> float | None:
    if abs(b) < 1e-12:
        return None
    return a / b


def metric(group: list[Cycle]) -> dict[str, Any]:
    closed = len(group)
    wins = [c for c in group if c.net_pnl > 0]
    losses = [c for c in group if c.net_pnl < 0]

    profit = sum(c.net_pnl for c in wins)
    loss = abs(sum(c.net_pnl for c in losses))

    gross = sum(c.gross_pnl for c in group)
    commission = sum(c.commission for c in group)
    net = sum(c.net_pnl for c in group)

    return {
        "closed": closed,
        "wins": len(wins),
        "losses": len(losses),
        "winrate": safe_div(len(wins), closed) or 0.0,
        "profit_factor": safe_div(profit, loss),
        "gross": gross,
        "commission": commission,
        "net": net,
        "avg_gross": safe_div(gross, closed) or 0.0,
        "avg_commission": safe_div(commission, closed) or 0.0,
        "avg_net": safe_div(net, closed) or 0.0,
        "avg_duration": safe_div(sum(c.duration_sec for c in group), closed) or 0.0,
    }


def verdict(m: dict[str, Any]) -> tuple[str, str]:
    closed = int(m["closed"])
    net = float(m["net"])
    pf = m["profit_factor"]
    avg_gross = abs(float(m["avg_gross"]))
    avg_commission = float(m["avg_commission"])

    if closed < MIN_CYCLES:
        return "INSUFFICIENT_DATA", "too_few_closed_cycles"

    if net < 0 and pf is not None and pf < 1.0:
        return "REJECTED_NEGATIVE_SAMPLE", "negative_net_and_profit_factor_below_one"

    if avg_commission > 0 and avg_gross < avg_commission:
        return "FEE_DRAG_DOMINATES", "avg_gross_below_avg_commission"

    if net > 0 and pf is not None and pf >= 1.2:
        return "CLEAN_RESEARCH_CANDIDATE", "clean_positive_after_commission"

    return "RESEARCH_ONLY_REVIEW", "mixed_or_unconfirmed_metrics"


def main() -> int:
    print("=== CLEAN RUNTIME SIGNAL CLASS EDGE SCORECARD V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print(f"min_cycles={MIN_CYCLES}")
    print("trade_source_class=RUNTIME_OR_PAPER_CLEAN_ENOUGH")
    print()

    trades = load_trades()
    cycles = reconstruct_cycles(trades)

    grouped: dict[tuple[str, str, str, str, str, str, str, str], list[Cycle]] = defaultdict(list)

    for c in cycles:
        key = (
            c.symbol,
            c.strategy,
            c.timeframe,
            c.continuous_symbol,
            c.entry_source,
            c.entry_signal_class,
            c.entry_regime,
            c.exit_signal_class,
        )
        grouped[key].append(c)

    counters: dict[str, int] = defaultdict(int)
    rows = []

    for key, group in grouped.items():
        m = metric(group)
        v, reason = verdict(m)
        counters[v] += 1
        rows.append((key, m, v, reason))

    rows.sort(key=lambda x: (x[2], -int(x[1]["closed"]), float(x[1]["net"])))

    print("CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_ROWS")

    for key, m, v, reason in rows:
        symbol, strategy, timeframe, continuous_symbol, entry_source, entry_signal_class, entry_regime, exit_signal_class = key
        pf = m["profit_factor"]

        print(
            "CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_ROW "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"continuous_symbol={continuous_symbol} "
            f"entry_source={entry_source} "
            f"entry_signal_class={entry_signal_class} "
            f"entry_regime={entry_regime} "
            f"exit_signal_class={exit_signal_class} "
            f"closed_cycles={m['closed']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"winrate={m['winrate']:.4f} "
            f"profit_factor={'NULL' if pf is None else f'{pf:.6f}'} "
            f"gross_pnl={m['gross']:.6f} "
            f"commission={m['commission']:.6f} "
            f"net_pnl={m['net']:.6f} "
            f"avg_gross_per_cycle={m['avg_gross']:.6f} "
            f"avg_commission_per_cycle={m['avg_commission']:.6f} "
            f"avg_net_per_cycle={m['avg_net']:.6f} "
            f"avg_duration_sec={m['avg_duration']:.2f} "
            f"verdict={v} "
            f"reason={reason}"
        )

    total_net = sum(c.net_pnl for c in cycles)
    total_commission = sum(c.commission for c in cycles)

    print()
    print("CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_SCORECARD_SUMMARY")
    print(f"trades_clean_runtime_or_paper={len(trades)}")
    print(f"closed_cycles_total={len(cycles)}")
    print(f"groups_total={len(grouped)}")
    print(f"clean_research_candidates={counters['CLEAN_RESEARCH_CANDIDATE']}")
    print(f"rejected_negative_rows={counters['REJECTED_NEGATIVE_SAMPLE']}")
    print(f"fee_drag_rows={counters['FEE_DRAG_DOMINATES']}")
    print(f"insufficient_data_rows={counters['INSUFFICIENT_DATA']}")
    print(f"research_only_review_rows={counters['RESEARCH_ONLY_REVIEW']}")
    print(f"net_pnl_total={total_net:.6f}")
    print(f"commission_total={total_commission:.6f}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if counters["CLEAN_RESEARCH_CANDIDATE"] > 0:
        print("VERDICT=CLEAN_RUNTIME_EDGE_HAS_RESEARCH_CANDIDATES")
    elif counters["REJECTED_NEGATIVE_SAMPLE"] > 0:
        print("VERDICT=CLEAN_RUNTIME_EDGE_NO_CANDIDATES_NEGATIVE_DOMINATES")
    else:
        print("VERDICT=CLEAN_RUNTIME_EDGE_NO_CANDIDATES")

    print("CLEAN_RUNTIME_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
