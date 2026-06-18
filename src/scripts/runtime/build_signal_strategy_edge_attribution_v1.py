#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SIGNAL_STRATEGY_EDGE_ATTRIBUTION_V1
# Read-only отчёт: какой signal/source/reason соответствует какой стратегии
# и какой net/gross/commission даёт этот класс сигнала.
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
    trade_source,
    origin,
    payload
from trades
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
  and coalesce(strategy, '') <> ''
  and coalesce(timeframe, '') <> ''
order by created_at asc, id asc;
"""


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
    if not isinstance(payload, dict):
        return default

    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)

    return cur if cur is not None else default


def extract_signal_class(row: dict[str, Any]) -> dict[str, str]:
    payload = row.get("payload")
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
        or row.get("trade_source")
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

    signal_id = (
        payload.get("signal_id")
        or payload.get("source_signal_id")
        or row.get("fill_id")
        or "UNKNOWN_SIGNAL_ID"
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
        "signal_source": sval(source),
        "signal_reason": sval(reason),
        "signal_id": sval(signal_id),
        "regime": sval(regime),
        "entry_gate": sval(entry_gate),
    }


def classify_row(row: dict[str, Any]) -> tuple[str, str]:
    trades = int(row["trades"])
    net = float(row["net_pnl"])
    gross = float(row["gross_pnl"])
    commission = float(row["commission"])
    avg_gross = gross / trades if trades else 0.0
    avg_comm = commission / trades if trades else 0.0

    if trades < 3:
        return "INSUFFICIENT_DATA", "too_few_trades"

    if net < 0 and abs(avg_gross) < avg_comm:
        return "FEE_DRAG_DOMINATES", "average_gross_smaller_than_commission"

    if gross < 0:
        return "NEGATIVE_GROSS_SIGNAL", "gross_negative_before_commission"

    if net > 0 and gross > commission:
        return "SIGNAL_RESEARCH_CANDIDATE", "positive_after_commission"

    return "REVIEW_REQUIRED", "mixed_signal_metrics"


def main() -> int:
    print("=== SIGNAL STRATEGY EDGE ATTRIBUTION V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL)
            rows = cur.fetchall()

    grouped: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}

    for row in rows:
        signal = extract_signal_class(row)

        key = (
            sval(row.get("symbol")),
            sval(row.get("strategy")),
            sval(row.get("timeframe")),
            signal["signal_source"],
            signal["signal_reason"],
            signal["regime"],
        )

        item = grouped.setdefault(
            key,
            {
                "symbol": key[0],
                "strategy": key[1],
                "timeframe": key[2],
                "signal_source": key[3],
                "signal_reason": key[4],
                "regime": key[5],
                "trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "gross_pnl": 0.0,
                "commission": 0.0,
                "net_pnl": 0.0,
                "first_trade": row.get("created_at"),
                "last_trade": row.get("created_at"),
                "sample_signal_id": signal["signal_id"],
                "sample_entry_gate": signal["entry_gate"],
            },
        )

        side = sval(row.get("side"))
        qty = fnum(row.get("qty"))
        price = fnum(row.get("price"))
        commission = fnum(row.get("commission"))

        # Русский комментарий:
        # На уровне signal attribution мы не реконструируем FIFO-cycle.
        # Здесь считаем торговую нагрузку/комиссионную стоимость сигнал-класса.
        # PnL по закрытым циклам остаётся в edge_audit_scorecard_v1.
        item["trades"] += 1
        item["commission"] += commission
        item["net_pnl"] -= commission

        if side == "BUY":
            item["buy_trades"] += 1
        elif side == "SELL":
            item["sell_trades"] += 1

        if row.get("created_at") < item["first_trade"]:
            item["first_trade"] = row.get("created_at")
        if row.get("created_at") > item["last_trade"]:
            item["last_trade"] = row.get("created_at")

    result_rows = []
    for item in grouped.values():
        verdict, reason = classify_row(item)
        item["verdict"] = verdict
        item["verdict_reason"] = reason
        result_rows.append(item)

    result_rows.sort(key=lambda r: (r["strategy"], r["symbol"], r["signal_source"], r["signal_reason"]))

    print("SIGNAL_STRATEGY_ATTRIBUTION_ROWS")
    for r in result_rows:
        print(
            "SIGNAL_STRATEGY_ATTRIBUTION_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"signal_source={r['signal_source']} "
            f"signal_reason={r['signal_reason']} "
            f"regime={r['regime']} "
            f"trades={r['trades']} "
            f"buy_trades={r['buy_trades']} "
            f"sell_trades={r['sell_trades']} "
            f"commission={r['commission']:.6f} "
            f"net_cost={r['net_pnl']:.6f} "
            f"sample_signal_id={r['sample_signal_id']} "
            f"sample_entry_gate={r['sample_entry_gate']} "
            f"first_trade={r['first_trade']} "
            f"last_trade={r['last_trade']} "
            f"verdict={r['verdict']} "
            f"reason={r['verdict_reason']}"
        )

    unknown_rows = sum(
        1 for r in result_rows
        if r["signal_source"].startswith("UNKNOWN") or r["signal_reason"].startswith("UNKNOWN")
    )
    fee_drag_rows = sum(1 for r in result_rows if r["verdict"] == "FEE_DRAG_DOMINATES")
    candidates = sum(1 for r in result_rows if r["verdict"] == "SIGNAL_RESEARCH_CANDIDATE")
    total_trades = sum(r["trades"] for r in result_rows)
    total_commission = sum(r["commission"] for r in result_rows)

    print()
    print("SIGNAL_STRATEGY_ATTRIBUTION_SUMMARY")
    print(f"rows={len(result_rows)}")
    print(f"trades_total={total_trades}")
    print(f"unknown_signal_rows={unknown_rows}")
    print(f"fee_drag_signal_rows={fee_drag_rows}")
    print(f"research_candidates={candidates}")
    print(f"commission_total={total_commission:.6f}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if unknown_rows > 0:
        print("VERDICT=SIGNAL_STRATEGY_ATTRIBUTION_HAS_UNKNOWN_SIGNALS")
    elif candidates > 0:
        print("VERDICT=SIGNAL_STRATEGY_ATTRIBUTION_HAS_RESEARCH_CANDIDATES")
    elif fee_drag_rows > 0:
        print("VERDICT=SIGNAL_STRATEGY_ATTRIBUTION_FEE_DRAG_DOMINATES")
    else:
        print("VERDICT=SIGNAL_STRATEGY_ATTRIBUTION_NO_CANDIDATES")

    print("SIGNAL_STRATEGY_EDGE_ATTRIBUTION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
