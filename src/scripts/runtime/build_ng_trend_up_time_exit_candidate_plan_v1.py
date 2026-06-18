#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# NG_TREND_UP_TIME_EXIT_RESEARCH_CANDIDATE_PLAN_V1
# Read-only план проверки NG research-candidate:
# smart_entry_retest + trend_up_high_vol + time_exit.
# Ничего не меняет в БД, runtime, execution и real trading.


TARGET_SYMBOL_PREFIX = "NG"
TARGET_STRATEGY = "NG_CONSERVATIVE_BREAKOUT_M1"
TARGET_ENTRY_SOURCE = "smart_entry_retest"
TARGET_ENTRY_REASON = "smart_entry_retest"
TARGET_ENTRY_REGIME = "trend_up_high_vol"
TARGET_EXIT_REASON = "time_exit"

LOOKBACK_DAYS = int(os.getenv("NG_TREND_UP_TIME_EXIT_LOOKBACK_DAYS", "30"))


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
    fill_id,
    payload
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
  and symbol like 'NG%%@RTSX'
  and strategy = %s
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
    side: str
    qty: float
    price: float
    commission: float
    signal_source: str
    signal_reason: str
    regime: str
    entry_gate: str


@dataclass
class Cycle:
    symbol: str
    strategy: str
    timeframe: str
    entry_source: str
    entry_reason: str
    entry_regime: str
    entry_gate: str
    exit_source: str
    exit_reason: str
    open_time: Any
    close_time: Any
    qty: float
    gross_pnl: float
    commission: float
    net_pnl: float
    duration_sec: float


def fnum(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def payload_get(payload: Any, *keys: str, default: Any = None) -> Any:
    cur = payload
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def extract_signal(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        payload = {}

    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
    signal_quality = payload.get("signal_quality_snapshot") if isinstance(payload.get("signal_quality_snapshot"), dict) else {}
    edge_gate = payload_get(payload, "trade_context_snapshot", "edge_gate", default={})
    if not isinstance(edge_gate, dict):
        edge_gate = {}

    source = (
        payload.get("source")
        or payload.get("entry_source")
        or signal_quality.get("source")
        or features.get("source")
        or "UNKNOWN_SOURCE"
    )

    reason = (
        payload.get("reason")
        or payload.get("entry_reason")
        or features.get("entry_reason")
        or features.get("reason")
        or edge_gate.get("reason")
        or "UNKNOWN_REASON"
    )

    regime = (
        features.get("regime")
        or features.get("regime_label")
        or payload.get("regime")
        or edge_gate.get("regime")
        or "UNKNOWN_REGIME"
    )

    entry_gate = (
        features.get("entry_gate")
        or features.get("entry_gate_reason")
        or edge_gate.get("reason")
        or "UNKNOWN_ENTRY_GATE"
    )

    return {
        "source": sval(source),
        "reason": sval(reason),
        "regime": sval(regime),
        "entry_gate": sval(entry_gate),
    }


def load_trades() -> list[Trade]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL, (interval, TARGET_STRATEGY))
            rows = cur.fetchall()

    result: list[Trade] = []
    for row in rows:
        sig = extract_signal(row.get("payload"))
        result.append(
            Trade(
                id=int(row["id"]),
                created_at=row["created_at"],
                symbol=sval(row.get("symbol")),
                strategy=sval(row.get("strategy")),
                timeframe=sval(row.get("timeframe")),
                side=sval(row.get("side")).upper(),
                qty=fnum(row.get("qty")),
                price=fnum(row.get("price")),
                commission=fnum(row.get("commission")),
                signal_source=sig["source"],
                signal_reason=sig["reason"],
                regime=sig["regime"],
                entry_gate=sig["entry_gate"],
            )
        )

    return result


def reconstruct_cycles(trades: list[Trade]) -> list[Cycle]:
    inventory: dict[tuple[str, str, str], deque[Trade]] = defaultdict(deque)
    cycles: list[Cycle] = []

    for trade in trades:
        key = (trade.symbol, trade.strategy, trade.timeframe)

        if trade.side == "BUY":
            inventory[key].append(trade)
            continue

        if trade.side == "SELL":
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
                        entry_source=entry.signal_source,
                        entry_reason=entry.signal_reason,
                        entry_regime=entry.regime,
                        entry_gate=entry.entry_gate,
                        exit_source=trade.signal_source,
                        exit_reason=trade.signal_reason,
                        open_time=entry.created_at,
                        close_time=trade.created_at,
                        qty=q,
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


def metrics_for(group: list[Cycle]) -> dict[str, Any]:
    closed = len(group)
    gross = sum(c.gross_pnl for c in group)
    commission = sum(c.commission for c in group)
    net = sum(c.net_pnl for c in group)
    wins = [c for c in group if c.net_pnl > 0]
    losses = [c for c in group if c.net_pnl < 0]

    gross_profit = sum(c.net_pnl for c in wins)
    gross_loss = abs(sum(c.net_pnl for c in losses))
    pf = safe_div(gross_profit, gross_loss)

    return {
        "closed_cycles": closed,
        "wins": len(wins),
        "losses": len(losses),
        "winrate": safe_div(len(wins), closed) or 0.0,
        "profit_factor": pf,
        "gross_pnl": gross,
        "commission": commission,
        "net_pnl": net,
        "avg_gross_per_cycle": safe_div(gross, closed) or 0.0,
        "avg_commission_per_cycle": safe_div(commission, closed) or 0.0,
        "avg_net_per_cycle": safe_div(net, closed) or 0.0,
        "avg_duration_sec": safe_div(sum(c.duration_sec for c in group), closed) or 0.0,
    }


def verdict_for(m: dict[str, Any], *, min_cycles: int = 20) -> tuple[str, str]:
    closed = int(m["closed_cycles"])
    net = float(m["net_pnl"])
    gross = float(m["gross_pnl"])
    avg_gross = float(m["avg_gross_per_cycle"])
    avg_commission = float(m["avg_commission_per_cycle"])
    pf = m["profit_factor"]

    # Русский комментарий:
    # Отрицательный net/PF имеет приоритет над малой выборкой.
    # Иначе отрицательный срез ошибочно выглядит как "просто ждём ещё данных".
    if closed > 0 and net < 0 and pf is not None and pf < 1.0:
        return "REJECTED_NEGATIVE_SAMPLE", "negative_net_and_profit_factor_below_one"

    if closed > 0 and net < 0 and abs(avg_gross) < avg_commission:
        return "FEE_DRAG_DOMINATES", "average_gross_smaller_than_commission"

    if closed < min_cycles:
        return "RESEARCH_ONLY_INSUFFICIENT_SAMPLE", "closed_cycles_below_minimum"

    if net > 0 and gross > avg_commission * closed and pf is not None and pf > 1.2:
        return "RESEARCH_CANDIDATE_CONFIRMED", "positive_after_commission_with_pf"

    return "REVIEW_REQUIRED", "mixed_metrics"


def main() -> int:
    print("=== NG TREND UP TIME EXIT RESEARCH CANDIDATE PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print(f"target_strategy={TARGET_STRATEGY}")
    print(f"target_entry_source={TARGET_ENTRY_SOURCE}")
    print(f"target_entry_reason={TARGET_ENTRY_REASON}")
    print(f"target_entry_regime={TARGET_ENTRY_REGIME}")
    print(f"target_exit_reason={TARGET_EXIT_REASON}")
    print()

    trades = load_trades()
    cycles = reconstruct_cycles(trades)

    target_cycles = [
        c for c in cycles
        if c.entry_source == TARGET_ENTRY_SOURCE
        and c.entry_reason == TARGET_ENTRY_REASON
        and c.entry_regime == TARGET_ENTRY_REGIME
        and c.exit_reason == TARGET_EXIT_REASON
    ]

    negative_sibling_cycles = [
        c for c in cycles
        if c.entry_source == TARGET_ENTRY_SOURCE
        and c.entry_reason == TARGET_ENTRY_REASON
        and c.entry_regime == TARGET_ENTRY_REGIME
        and c.exit_reason != TARGET_EXIT_REASON
    ]

    by_day: dict[str, list[Cycle]] = defaultdict(list)
    for c in target_cycles:
        day = str(c.close_time.date()) if hasattr(c.close_time, "date") else "UNKNOWN_DAY"
        by_day[day].append(c)

    target_metrics = metrics_for(target_cycles)
    sibling_metrics = metrics_for(negative_sibling_cycles)

    target_verdict, target_reason = verdict_for(target_metrics, min_cycles=20)
    sibling_verdict, sibling_reason = verdict_for(sibling_metrics, min_cycles=5)

    print("NG_TREND_UP_TIME_EXIT_TARGET_METRICS")
    pf = target_metrics["profit_factor"]
    print(f"closed_cycles={target_metrics['closed_cycles']}")
    print(f"wins={target_metrics['wins']}")
    print(f"losses={target_metrics['losses']}")
    print(f"winrate={target_metrics['winrate']:.4f}")
    print(f"profit_factor={'NULL' if pf is None else f'{pf:.6f}'}")
    print(f"gross_pnl={target_metrics['gross_pnl']:.6f}")
    print(f"commission={target_metrics['commission']:.6f}")
    print(f"net_pnl={target_metrics['net_pnl']:.6f}")
    print(f"avg_gross_per_cycle={target_metrics['avg_gross_per_cycle']:.6f}")
    print(f"avg_commission_per_cycle={target_metrics['avg_commission_per_cycle']:.6f}")
    print(f"avg_net_per_cycle={target_metrics['avg_net_per_cycle']:.6f}")
    print(f"avg_duration_sec={target_metrics['avg_duration_sec']:.2f}")
    print(f"target_verdict={target_verdict}")
    print(f"target_reason={target_reason}")
    print()

    print("NG_TREND_UP_TIME_EXIT_DAY_ROWS")
    for day, group in sorted(by_day.items()):
        m = metrics_for(group)
        day_pf = m["profit_factor"]
        print(
            "NG_TREND_UP_TIME_EXIT_DAY_ROW "
            f"day={day} "
            f"closed_cycles={m['closed_cycles']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"winrate={m['winrate']:.4f} "
            f"profit_factor={'NULL' if day_pf is None else f'{day_pf:.6f}'} "
            f"gross_pnl={m['gross_pnl']:.6f} "
            f"commission={m['commission']:.6f} "
            f"net_pnl={m['net_pnl']:.6f} "
            f"avg_net_per_cycle={m['avg_net_per_cycle']:.6f}"
        )

    print()
    print("NG_TREND_UP_SIBLING_EXIT_METRICS")
    sibling_pf = sibling_metrics["profit_factor"]
    print(f"closed_cycles={sibling_metrics['closed_cycles']}")
    print(f"wins={sibling_metrics['wins']}")
    print(f"losses={sibling_metrics['losses']}")
    print(f"winrate={sibling_metrics['winrate']:.4f}")
    print(f"profit_factor={'NULL' if sibling_pf is None else f'{sibling_pf:.6f}'}")
    print(f"gross_pnl={sibling_metrics['gross_pnl']:.6f}")
    print(f"commission={sibling_metrics['commission']:.6f}")
    print(f"net_pnl={sibling_metrics['net_pnl']:.6f}")
    print(f"avg_net_per_cycle={sibling_metrics['avg_net_per_cycle']:.6f}")
    print(f"sibling_verdict={sibling_verdict}")
    print(f"sibling_reason={sibling_reason}")

    print()
    print("NG_TREND_UP_TIME_EXIT_RECOMMENDATION")
    print("recommended_status=KEEP_RESEARCH_ONLY")
    print("recommended_min_closed_cycles=20")
    print("recommended_no_runtime_promotion=1")
    print("recommended_collect_more_data=1")
    print("recommended_candidate_filter=entry_regime:trend_up_high_vol,exit_reason:time_exit")
    print("recommended_block_or_review_sibling_exit=stop_loss_long")
    print("recommended_real_trading_enabled=0")
    print("recommended_execution_enabled=0")
    print("recommended_db_update=0")

    print()
    print("NG_TREND_UP_TIME_EXIT_PLAN_SUMMARY")
    print(f"target_closed_cycles={target_metrics['closed_cycles']}")
    print(f"target_net_pnl={target_metrics['net_pnl']:.6f}")
    print(f"target_profit_factor={'NULL' if pf is None else f'{pf:.6f}'}")
    print(f"days_with_target={len(by_day)}")
    print(f"sibling_closed_cycles={sibling_metrics['closed_cycles']}")
    print(f"sibling_net_pnl={sibling_metrics['net_pnl']:.6f}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if target_verdict == "RESEARCH_CANDIDATE_CONFIRMED":
        print("VERDICT=NG_TREND_UP_TIME_EXIT_CANDIDATE_CONFIRMED")
    elif target_verdict in {"REJECTED_NEGATIVE_SAMPLE", "FEE_DRAG_DOMINATES"}:
        print("VERDICT=NG_TREND_UP_TIME_EXIT_CANDIDATE_REJECTED")
    elif target_metrics["closed_cycles"] > 0:
        print("VERDICT=NG_TREND_UP_TIME_EXIT_KEEP_RESEARCH_ONLY")
    else:
        print("VERDICT=NG_TREND_UP_TIME_EXIT_NO_CANDIDATE_DATA")

    print("NG_TREND_UP_TIME_EXIT_RESEARCH_CANDIDATE_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
