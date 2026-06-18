#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# NORMALIZED_SIGNAL_CLASS_EDGE_SCORECARD_V1
# Read-only scorecard по нормализованным payload.signal_class.
# Цель: оценить edge по устойчивым signal_class, а не по сырому reason.
# Никаких UPDATE. Реальная торговля и execution не включаются.


LOOKBACK_DAYS = int(os.getenv("NORMALIZED_SIGNAL_CLASS_EDGE_LOOKBACK_DAYS", "30"))
MIN_CYCLES = int(os.getenv("NORMALIZED_SIGNAL_CLASS_EDGE_MIN_CYCLES", "5"))


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


UNKNOWN_REVIEW_SQL = """
select
    count(*) as unknown_review_rows
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
  and not (payload ? 'signal_class');
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
    signal_params: dict[str, Any]


@dataclass
class Cycle:
    symbol: str
    strategy: str
    timeframe: str
    continuous_symbol: str
    entry_signal_class: str
    entry_source: str
    entry_regime: str
    exit_signal_class: str
    exit_source: str
    exit_regime: str
    qty: float
    gross_pnl: float
    commission: float
    net_pnl: float
    duration_sec: float
    open_time: Any
    close_time: Any


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


def extract_trade(row: dict[str, Any]) -> Trade:
    payload = payload_dict(row.get("payload"))

    signal_params = payload.get("signal_params")
    if not isinstance(signal_params, dict):
        signal_params = {}

    return Trade(
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
        signal_params=signal_params,
    )


def load_data() -> tuple[list[Trade], int]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL, (interval,))
            trade_rows = list(cur.fetchall())

            cur.execute(UNKNOWN_REVIEW_SQL, (interval,))
            unknown_row = cur.fetchone() or {}

    return [extract_trade(row) for row in trade_rows], int(unknown_row.get("unknown_review_rows") or 0)


def reconstruct_cycles(trades: list[Trade]) -> list[Cycle]:
    # Русский комментарий:
    # FIFO long-only реконструкция циклов: BUY открывает, SELL закрывает.
    # Для текущих paper/live потоков этого достаточно.
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
                    entry_signal_class=entry.signal_class,
                    entry_source=entry.entry_source,
                    entry_regime=entry.entry_regime,
                    exit_signal_class=trade.signal_class,
                    exit_source=trade.entry_source,
                    exit_regime=trade.entry_regime,
                    qty=q,
                    gross_pnl=gross,
                    commission=commission,
                    net_pnl=net,
                    duration_sec=duration,
                    open_time=entry.created_at,
                    close_time=trade.created_at,
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

    gross_profit = sum(c.net_pnl for c in wins)
    gross_loss = abs(sum(c.net_pnl for c in losses))

    gross = sum(c.gross_pnl for c in group)
    commission = sum(c.commission for c in group)
    net = sum(c.net_pnl for c in group)

    return {
        "closed_cycles": closed,
        "wins": len(wins),
        "losses": len(losses),
        "winrate": safe_div(len(wins), closed) or 0.0,
        "profit_factor": safe_div(gross_profit, gross_loss),
        "gross_pnl": gross,
        "commission": commission,
        "net_pnl": net,
        "avg_gross_per_cycle": safe_div(gross, closed) or 0.0,
        "avg_commission_per_cycle": safe_div(commission, closed) or 0.0,
        "avg_net_per_cycle": safe_div(net, closed) or 0.0,
        "avg_duration_sec": safe_div(sum(c.duration_sec for c in group), closed) or 0.0,
    }


def verdict(
    m: dict[str, Any],
    *,
    entry_source: str,
    entry_regime: str,
    strategy: str,
    timeframe: str,
) -> tuple[str, str]:
    closed = int(m["closed_cycles"])
    net = float(m["net_pnl"])
    gross = float(m["gross_pnl"])
    commission = float(m["commission"])
    avg_gross = float(m["avg_gross_per_cycle"])
    avg_commission = float(m["avg_commission_per_cycle"])
    avg_duration = float(m["avg_duration_sec"])
    pf = m["profit_factor"]

    is_historical = entry_source == "historical_signal_replay_backfill"
    is_unknown_source = entry_source == "UNKNOWN_SOURCE"
    is_unknown_regime = entry_regime in {"UNKNOWN", "UNKNOWN_REGIME"}
    is_missing_context = (
        strategy in {"", "UNKNOWN", "UNKNOWN_STRATEGY"}
        or timeframe in {"", "UNKNOWN", "UNKNOWN_TIMEFRAME"}
    )

    # Русский комментарий:
    # Положительный результат без source/commission/duration нельзя считать edge.
    # Это dirty/legacy слой, который требует отдельной валидации.
    if is_unknown_source and commission == 0.0 and avg_duration == 0.0:
        return "DIRTY_DATA_REVIEW_ONLY", "unknown_source_zero_commission_zero_duration"

    if is_missing_context:
        return "DIRTY_DATA_REVIEW_ONLY", "missing_strategy_or_timeframe"

    if closed < MIN_CYCLES:
        return "INSUFFICIENT_DATA", "too_few_closed_cycles"

    if net < 0 and pf is not None and pf < 1.0:
        return "REJECTED_NEGATIVE_SAMPLE", "negative_net_and_profit_factor_below_one"

    if abs(avg_gross) < avg_commission:
        return "FEE_DRAG_DOMINATES", "average_gross_smaller_than_commission"

    if is_historical:
        if net > 0 and gross > 0 and pf is not None and pf >= 1.20:
            return "HISTORICAL_RESEARCH_CANDIDATE", "historical_positive_before_runtime_validation"
        return "HISTORICAL_REVIEW_REQUIRED", "historical_mixed_metrics"

    if is_unknown_source or is_unknown_regime:
        return "DIRTY_DATA_REVIEW_ONLY", "unknown_source_or_regime"

    if net > 0 and gross > 0 and pf is not None and pf >= 1.20 and avg_gross > avg_commission:
        return "RESEARCH_CANDIDATE", "positive_after_commission"

    return "REVIEW_REQUIRED", "mixed_metrics"


def main() -> int:
    print("=== NORMALIZED SIGNAL CLASS EDGE SCORECARD V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print(f"min_cycles={MIN_CYCLES}")
    print()

    trades, unknown_review_rows = load_data()
    cycles = reconstruct_cycles(trades)

    grouped: dict[tuple[str, str, str, str, str, str, str, str], list[Cycle]] = defaultdict(list)

    for cycle in cycles:
        key = (
            cycle.symbol,
            cycle.strategy,
            cycle.timeframe,
            cycle.continuous_symbol,
            cycle.entry_source,
            cycle.entry_signal_class,
            cycle.entry_regime,
            cycle.exit_signal_class,
        )
        grouped[key].append(cycle)

    print("NORMALIZED_SIGNAL_CLASS_EDGE_ROWS")

    research_candidates = 0
    historical_research_candidates = 0
    dirty_data_review_rows = 0
    rejected_negative = 0
    fee_drag_rows = 0
    insufficient_rows = 0
    review_required = 0

    total_closed = 0
    total_net = 0.0
    total_commission = 0.0

    rows = []

    for key, group in grouped.items():
        m = metrics(group)
        symbol, strategy, timeframe, continuous_symbol, entry_source, entry_signal_class, entry_regime, exit_signal_class = key
        v, reason = verdict(
            m,
            entry_source=entry_source,
            entry_regime=entry_regime,
            strategy=strategy,
            timeframe=timeframe,
        )

        if v == "RESEARCH_CANDIDATE":
            research_candidates += 1
        elif v == "HISTORICAL_RESEARCH_CANDIDATE":
            historical_research_candidates += 1
        elif v == "DIRTY_DATA_REVIEW_ONLY":
            dirty_data_review_rows += 1
        elif v == "REJECTED_NEGATIVE_SAMPLE":
            rejected_negative += 1
        elif v == "FEE_DRAG_DOMINATES":
            fee_drag_rows += 1
        elif v == "INSUFFICIENT_DATA":
            insufficient_rows += 1
        else:
            review_required += 1

        total_closed += int(m["closed_cycles"])
        total_net += float(m["net_pnl"])
        total_commission += float(m["commission"])

        rows.append((key, m, v, reason))

    rows.sort(
        key=lambda x: (
            0 if x[2] == "RESEARCH_CANDIDATE" else
            1 if x[2] == "HISTORICAL_RESEARCH_CANDIDATE" else
            2 if x[2] == "DIRTY_DATA_REVIEW_ONLY" else
            3,
            -int(x[1]["closed_cycles"]),
            float(x[1]["net_pnl"]),
        )
    )

    for key, m, v, reason in rows:
        symbol, strategy, timeframe, continuous_symbol, entry_source, entry_signal_class, entry_regime, exit_signal_class = key
        pf = m["profit_factor"]

        print(
            "NORMALIZED_SIGNAL_CLASS_EDGE_ROW "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"continuous_symbol={continuous_symbol} "
            f"entry_source={entry_source} "
            f"entry_signal_class={entry_signal_class} "
            f"entry_regime={entry_regime} "
            f"exit_signal_class={exit_signal_class} "
            f"closed_cycles={m['closed_cycles']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"winrate={m['winrate']:.4f} "
            f"profit_factor={'NULL' if pf is None else f'{pf:.6f}'} "
            f"gross_pnl={m['gross_pnl']:.6f} "
            f"commission={m['commission']:.6f} "
            f"net_pnl={m['net_pnl']:.6f} "
            f"avg_gross_per_cycle={m['avg_gross_per_cycle']:.6f} "
            f"avg_commission_per_cycle={m['avg_commission_per_cycle']:.6f} "
            f"avg_net_per_cycle={m['avg_net_per_cycle']:.6f} "
            f"avg_duration_sec={m['avg_duration_sec']:.2f} "
            f"verdict={v} "
            f"reason={reason}"
        )

    print()
    print("NORMALIZED_SIGNAL_CLASS_EDGE_SCORECARD_SUMMARY")
    print(f"trades_with_signal_class={len(trades)}")
    print(f"unknown_review_rows={unknown_review_rows}")
    print(f"closed_cycles_total={total_closed}")
    print(f"groups_total={len(grouped)}")
    print(f"research_candidates={research_candidates}")
    print(f"historical_research_candidates={historical_research_candidates}")
    print(f"dirty_data_review_rows={dirty_data_review_rows}")
    print(f"rejected_negative_rows={rejected_negative}")
    print(f"fee_drag_rows={fee_drag_rows}")
    print(f"insufficient_data_rows={insufficient_rows}")
    print(f"review_required_rows={review_required}")
    print(f"net_pnl_total={total_net:.6f}")
    print(f"commission_total={total_commission:.6f}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if research_candidates > 0:
        print("VERDICT=NORMALIZED_SIGNAL_CLASS_EDGE_HAS_CLEAN_RESEARCH_CANDIDATES")
    elif historical_research_candidates > 0 or dirty_data_review_rows > 0:
        print("VERDICT=NORMALIZED_SIGNAL_CLASS_EDGE_HAS_DIRTY_OR_HISTORICAL_CANDIDATES_ONLY")
    elif rejected_negative > 0 or fee_drag_rows > 0:
        print("VERDICT=NORMALIZED_SIGNAL_CLASS_EDGE_NO_CONFIRMED_CANDIDATES")
    elif unknown_review_rows > 0 and total_closed == 0:
        print("VERDICT=NORMALIZED_SIGNAL_CLASS_EDGE_INSUFFICIENT_NORMALIZED_DATA")
    else:
        print("VERDICT=NORMALIZED_SIGNAL_CLASS_EDGE_REVIEW_REQUIRED")

    print("NORMALIZED_SIGNAL_CLASS_EDGE_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
