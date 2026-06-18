#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1
# Read-only план решений по нормализованным signal_class.
# Ничего не меняет в БД. Не включает runtime/execution.


LOOKBACK_DAYS = int(os.getenv("SIGNAL_CLASS_CANDIDATE_LOOKBACK_DAYS", "30"))
MIN_CYCLES = int(os.getenv("SIGNAL_CLASS_CANDIDATE_MIN_CYCLES", "5"))


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
    commission,
    payload
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
  and payload ? 'signal_class'
  and coalesce(payload->>'signal_class', '') <> ''
  and payload->>'signal_class' <> 'UNKNOWN_REASON'
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
            cur.execute(TRADES_SQL, (interval,))
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
                signal_class=sval(payload.get("signal_class"), "UNKNOWN_REASON"),
                entry_source=sval(payload.get("entry_source_normalized"), "UNKNOWN_SOURCE"),
                entry_regime=sval(payload.get("entry_regime_normalized"), "UNKNOWN_REGIME"),
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
            q = min(qty_left, entry.qty)

            gross = (trade.price - entry.price) * q
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

            entry.qty -= q
            qty_left -= q

            if entry.qty <= 1e-12:
                inventory[key].popleft()

    return cycles


def safe_div(a: float, b: float) -> float | None:
    if abs(b) < 1e-12:
        return None
    return a / b


def metrics(group: list[Cycle]) -> dict[str, Any]:
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
        "avg_net": safe_div(net, closed) or 0.0,
        "avg_commission": safe_div(commission, closed) or 0.0,
        "avg_duration": safe_div(sum(c.duration_sec for c in group), closed) or 0.0,
    }


def decision_for(key: tuple[str, ...], m: dict[str, Any]) -> tuple[str, str]:
    symbol, strategy, timeframe, continuous_symbol, entry_source, signal_class, entry_regime, exit_signal_class = key

    closed = int(m["closed"])
    net = float(m["net"])
    commission = float(m["commission"])
    avg_duration = float(m["avg_duration"])
    pf = m["profit_factor"]

    if entry_source == "UNKNOWN_SOURCE" and commission == 0.0 and avg_duration == 0.0:
        return "DIRTY_DATA_REVIEW", "unknown_source_zero_commission_zero_duration"

    if entry_source == "historical_signal_replay_backfill":
        if closed >= MIN_CYCLES and net > 0 and pf is not None and pf >= 1.2:
            return "KEEP_HISTORICAL_RESEARCH_ONLY", "historical_positive_requires_replay_validation"
        return "HISTORICAL_REVIEW_REQUIRED", "historical_not_strong_enough"

    if closed < MIN_CYCLES:
        return "REQUIRE_MORE_DATA", "too_few_closed_cycles"

    if net < 0 and pf is not None and pf < 1.0:
        return "QUARANTINE_SIGNAL_CLASS", "negative_net_and_profit_factor_below_one"

    if net > 0 and pf is not None and pf >= 1.2 and commission > 0:
        return "PROMOTE_TO_RESEARCH_CANDIDATE", "clean_positive_after_commission"

    return "KEEP_RESEARCH_ONLY", "mixed_or_unconfirmed_metrics"


def main() -> int:
    print("=== SIGNAL CLASS STRATEGY CANDIDATE PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print(f"min_cycles={MIN_CYCLES}")
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

    counters = defaultdict(int)

    print("SIGNAL_CLASS_STRATEGY_CANDIDATE_ROWS")

    rows = []
    for key, group in grouped.items():
        m = metrics(group)
        action, reason = decision_for(key, m)
        counters[action] += 1
        rows.append((key, m, action, reason))

    rows.sort(
        key=lambda x: (
            x[2],
            -int(x[1]["closed"]),
            float(x[1]["net"]),
        )
    )

    for key, m, action, reason in rows:
        symbol, strategy, timeframe, continuous_symbol, entry_source, signal_class, entry_regime, exit_signal_class = key
        pf = m["profit_factor"]

        print(
            "SIGNAL_CLASS_STRATEGY_CANDIDATE_ROW "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"continuous_symbol={continuous_symbol} "
            f"entry_source={entry_source} "
            f"signal_class={signal_class} "
            f"entry_regime={entry_regime} "
            f"exit_signal_class={exit_signal_class} "
            f"closed_cycles={m['closed']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"winrate={m['winrate']:.4f} "
            f"profit_factor={'NULL' if pf is None else f'{pf:.6f}'} "
            f"net_pnl={m['net']:.6f} "
            f"commission={m['commission']:.6f} "
            f"avg_net={m['avg_net']:.6f} "
            f"avg_duration_sec={m['avg_duration']:.2f} "
            f"planned_action={action} "
            f"reason={reason}"
        )

    print()
    print("SIGNAL_CLASS_STRATEGY_CANDIDATE_SUMMARY")
    print(f"groups_total={len(grouped)}")
    print(f"promote_to_research_candidate={counters['PROMOTE_TO_RESEARCH_CANDIDATE']}")
    print(f"keep_historical_research_only={counters['KEEP_HISTORICAL_RESEARCH_ONLY']}")
    print(f"historical_review_required={counters['HISTORICAL_REVIEW_REQUIRED']}")
    print(f"dirty_data_review={counters['DIRTY_DATA_REVIEW']}")
    print(f"quarantine_signal_class={counters['QUARANTINE_SIGNAL_CLASS']}")
    print(f"require_more_data={counters['REQUIRE_MORE_DATA']}")
    print(f"keep_research_only={counters['KEEP_RESEARCH_ONLY']}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if counters["PROMOTE_TO_RESEARCH_CANDIDATE"] > 0:
        print("VERDICT=SIGNAL_CLASS_STRATEGY_CANDIDATES_FOUND")
    elif counters["KEEP_HISTORICAL_RESEARCH_ONLY"] > 0 or counters["DIRTY_DATA_REVIEW"] > 0:
        print("VERDICT=SIGNAL_CLASS_STRATEGY_NO_CLEAN_CANDIDATES")
    else:
        print("VERDICT=SIGNAL_CLASS_STRATEGY_RESEARCH_ONLY")

    print("SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
