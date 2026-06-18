#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SIGNAL_CLASS_EDGE_SCORECARD_V1
# Read-only scorecard: entry signal class -> exit reason -> closed cycle PnL.
# Ничего не меняет в БД, runtime, execution и real trading.


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
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
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
    side: str
    qty: float
    price: float
    commission: float
    fill_id: str
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

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL)
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
                fill_id=sval(row.get("fill_id")),
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

    for t in trades:
        key = (t.symbol, t.strategy, t.timeframe)

        if t.side == "BUY":
            inventory[key].append(t)
            continue

        if t.side == "SELL":
            qty_left = t.qty
            while qty_left > 1e-12 and inventory[key]:
                entry = inventory[key][0]
                q = min(qty_left, entry.qty)

                gross = (t.price - entry.price) * q
                commission = entry.commission + t.commission
                net = gross - commission

                try:
                    duration = (t.created_at - entry.created_at).total_seconds()
                except Exception:
                    duration = 0.0

                cycles.append(
                    Cycle(
                        symbol=t.symbol,
                        strategy=t.strategy,
                        timeframe=t.timeframe,
                        entry_source=entry.signal_source,
                        entry_reason=entry.signal_reason,
                        entry_regime=entry.regime,
                        entry_gate=entry.entry_gate,
                        exit_source=t.signal_source,
                        exit_reason=t.signal_reason,
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


def verdict_for(closed: int, gross: float, commission: float, net: float, pf: float | None) -> tuple[str, str]:
    avg_gross = safe_div(gross, closed) or 0.0
    avg_commission = safe_div(commission, closed) or 0.0

    if closed < 3:
        return "INSUFFICIENT_DATA", "too_few_closed_cycles"

    if net < 0 and abs(avg_gross) < avg_commission:
        return "FEE_DRAG_DOMINATES", "average_gross_smaller_than_commission"

    if gross < 0:
        return "NEGATIVE_GROSS_EDGE", "gross_negative_before_commission"

    if pf is not None and pf < 1:
        return "NEGATIVE_EXPECTANCY", "profit_factor_below_one"

    if net > 0 and gross > commission:
        return "SIGNAL_CLASS_RESEARCH_CANDIDATE", "positive_after_commission"

    return "REVIEW_REQUIRED", "mixed_metrics"


def main() -> int:
    print("=== SIGNAL CLASS EDGE SCORECARD V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    trades = load_trades()
    cycles = reconstruct_cycles(trades)

    grouped: dict[tuple[str, str, str, str, str, str, str], list[Cycle]] = defaultdict(list)

    for c in cycles:
        key = (
            c.symbol,
            c.strategy,
            c.timeframe,
            c.entry_source,
            c.entry_reason,
            c.entry_regime,
            c.exit_reason,
        )
        grouped[key].append(c)

    rows: list[dict[str, Any]] = []
    for key, group in grouped.items():
        gross = sum(c.gross_pnl for c in group)
        commission = sum(c.commission for c in group)
        net = sum(c.net_pnl for c in group)
        wins = [c for c in group if c.net_pnl > 0]
        losses = [c for c in group if c.net_pnl < 0]
        closed = len(group)

        gross_profit = sum(c.net_pnl for c in wins)
        gross_loss = abs(sum(c.net_pnl for c in losses))
        pf = safe_div(gross_profit, gross_loss)

        verdict, reason = verdict_for(closed, gross, commission, net, pf)

        rows.append(
            {
                "symbol": key[0],
                "strategy": key[1],
                "timeframe": key[2],
                "entry_source": key[3],
                "entry_reason": key[4],
                "entry_regime": key[5],
                "exit_reason": key[6],
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
                "verdict": verdict,
                "reason": reason,
            }
        )

    rows.sort(key=lambda r: r["net_pnl"])

    print("SIGNAL_CLASS_EDGE_ROWS")
    for r in rows:
        pf_text = "NULL" if r["profit_factor"] is None else f"{r['profit_factor']:.6f}"
        print(
            "SIGNAL_CLASS_EDGE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"entry_source={r['entry_source']} "
            f"entry_reason={r['entry_reason']} "
            f"entry_regime={r['entry_regime']} "
            f"exit_reason={r['exit_reason']} "
            f"closed_cycles={r['closed_cycles']} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"winrate={r['winrate']:.4f} "
            f"profit_factor={pf_text} "
            f"gross_pnl={r['gross_pnl']:.6f} "
            f"commission={r['commission']:.6f} "
            f"net_pnl={r['net_pnl']:.6f} "
            f"avg_gross_per_cycle={r['avg_gross_per_cycle']:.6f} "
            f"avg_commission_per_cycle={r['avg_commission_per_cycle']:.6f} "
            f"avg_net_per_cycle={r['avg_net_per_cycle']:.6f} "
            f"avg_duration_sec={r['avg_duration_sec']:.2f} "
            f"verdict={r['verdict']} "
            f"reason={r['reason']}"
        )

    total_closed = sum(r["closed_cycles"] for r in rows)
    total_gross = sum(r["gross_pnl"] for r in rows)
    total_commission = sum(r["commission"] for r in rows)
    total_net = sum(r["net_pnl"] for r in rows)
    candidates = sum(1 for r in rows if r["verdict"] == "SIGNAL_CLASS_RESEARCH_CANDIDATE")
    fee_drag = sum(1 for r in rows if r["verdict"] == "FEE_DRAG_DOMINATES")
    insufficient = sum(1 for r in rows if r["verdict"] == "INSUFFICIENT_DATA")

    print()
    print("SIGNAL_CLASS_EDGE_SUMMARY")
    print(f"rows={len(rows)}")
    print(f"closed_cycles_total={total_closed}")
    print(f"gross_pnl_total={total_gross:.6f}")
    print(f"commission_total={total_commission:.6f}")
    print(f"net_pnl_total={total_net:.6f}")
    print(f"fee_drag_rows={fee_drag}")
    print(f"research_candidates={candidates}")
    print(f"insufficient_data_rows={insufficient}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if candidates > 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_HAS_RESEARCH_CANDIDATES")
    elif fee_drag > 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_FEE_DRAG_DOMINATES")
    elif insufficient == len(rows):
        print("VERDICT=SIGNAL_CLASS_EDGE_INSUFFICIENT_DATA")
    else:
        print("VERDICT=SIGNAL_CLASS_EDGE_NO_CONFIRMED_EDGE")

    print("SIGNAL_CLASS_EDGE_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
