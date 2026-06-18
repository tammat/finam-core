#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


# Русский комментарий:
# SIGNAL_CLASS_EDGE_SCORECARD_V1_1 — read-only scorecard по закрытым торговым цепочкам.
# В отличие от V1, здесь BUY/SELL ноги не разрываются по direction.
# Скрипт строит FIFO-пары внутри strategy/timeframe/continuous_symbol/symbol
# и считает edge по entry_signal_class -> exit_signal_class.


@dataclass(frozen=True)
class SignalClassRule:
    signal_class: str
    patterns: tuple[str, ...]


SIGNAL_CLASS_RULES: tuple[SignalClassRule, ...] = (
    SignalClassRule("GOLD_SHORT_SHADOW", ("gold_short_only_shadow_v1",)),
    SignalClassRule("TIME_EXIT", ("time_exit", "timeout", "time_stop")),
    SignalClassRule("SMART_ENTRY_RETEST", ("smart_entry_retest", "retest")),
    SignalClassRule("BREAKOUT", ("breakout", "break_out", "range_break", "level_break", "stop_loss_long")),
    SignalClassRule("BREAKDOWN", ("breakdown", "break_down")),
    SignalClassRule("FALSE_BREAKOUT", ("false_breakout", "fake_breakout", "false_break")),
    SignalClassRule("REVERSAL", ("reversal", "reverse", "pivot")),
    SignalClassRule("IMPULSE", ("impulse", "momentum", "acceleration")),
    SignalClassRule("VOLATILITY_COMPRESSION", ("compression", "squeeze", "low_vol")),
    SignalClassRule("VOLATILITY_EXPANSION", ("vol_expansion", "high_vol", "atr_expansion")),
    SignalClassRule("TREND_CONTINUATION", ("trend_continuation", "pullback", "continuation")),
    SignalClassRule("MEAN_REVERSION", ("mean_reversion", "revert", "vwap_bands", "mr")),
    SignalClassRule("RANGE_BOUNDARY_REACTION", ("range", "support", "resistance", "boundary")),
    SignalClassRule("SESSION_SIGNAL", ("session", "open", "close")),
    SignalClassRule("REGIME_FILTER", ("regime", "trend_up", "trend_down", "flat", "stall_exit")),
    SignalClassRule("CROSS_MARKET_CONFIRMATION", ("cross_market", "confirmation", "brent", "usd", "dxy")),
    SignalClassRule("LIQUIDITY_FILTER", ("liquidity", "spread", "slippage", "book")),
)


TRADES_SQL = """
WITH base AS (
    SELECT
        id,
        symbol,
        side,
        qty::numeric AS qty,
        price::numeric AS price,
        COALESCE(commission, 0)::numeric AS commission,
        origin,
        trade_source,
        strategy,
        timeframe,
        continuous_symbol,
        created_at,
        payload,
        COALESCE(
            NULLIF(payload->>'reason', ''),
            NULLIF(payload->>'signal_reason', ''),
            NULLIF(payload->>'entry_reason', ''),
            NULLIF(payload->>'exit_reason', ''),
            NULLIF(payload->'metadata'->>'reason', ''),
            NULLIF(payload->'metadata'->>'signal_reason', ''),
            NULLIF(payload->'trade_context_snapshot'->>'reason', ''),
            NULLIF(payload->'trade_context_snapshot'->>'signal_reason', '')
        ) AS signal_reason,
        COALESCE(
            NULLIF(strategy, ''),
            NULLIF(payload->>'strategy', ''),
            NULLIF(payload->'metadata'->>'strategy', ''),
            NULLIF(payload->'trade_context_snapshot'->>'strategy', ''),
            'UNKNOWN'
        ) AS resolved_strategy,
        COALESCE(
            NULLIF(timeframe, ''),
            NULLIF(payload->>'timeframe', ''),
            NULLIF(payload->'metadata'->>'timeframe', ''),
            NULLIF(payload->'trade_context_snapshot'->>'timeframe', ''),
            'UNKNOWN'
        ) AS resolved_timeframe,
        COALESCE(
            NULLIF(continuous_symbol, ''),
            NULLIF(payload->>'continuous_symbol', ''),
            NULLIF(payload->'metadata'->>'continuous_symbol', ''),
            NULLIF(payload->'trade_context_snapshot'->>'continuous_symbol', ''),
            symbol
        ) AS resolved_continuous_symbol
    FROM trades
    WHERE COALESCE(is_invalid, false) = false
      AND payload IS NOT NULL
      AND created_at >= now() - (%s::text)::interval
)
SELECT
    id,
    symbol,
    side,
    qty,
    price,
    commission,
    origin,
    trade_source,
    resolved_strategy AS strategy,
    resolved_timeframe AS timeframe,
    resolved_continuous_symbol AS continuous_symbol,
    signal_reason,
    created_at,
    payload
FROM base
ORDER BY resolved_strategy, resolved_timeframe, resolved_continuous_symbol, symbol, created_at, id
LIMIT %s;
"""


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def classify_signal(row: dict[str, Any]) -> str:
    reason = _lower(row.get("signal_reason"))
    strategy = _lower(row.get("strategy"))
    timeframe = _lower(row.get("timeframe"))
    symbol = _lower(row.get("symbol"))
    payload = row.get("payload") or {}

    candidates: list[str] = [reason, strategy, timeframe, symbol]

    if isinstance(payload, dict):
        for key in (
            "reason",
            "signal_reason",
            "entry_reason",
            "exit_reason",
            "intent_type",
            "source",
            "regime",
            "adaptive_regime_action",
            "adaptive_position_reason",
        ):
            value = payload.get(key)
            if value is not None:
                candidates.append(str(value).lower())

        features = payload.get("features")
        if isinstance(features, dict):
            for key, value in features.items():
                candidates.append(str(key).lower())
                if value is not None:
                    candidates.append(str(value).lower())

    haystack = " ".join(candidates)

    if not haystack.strip():
        return "NO_SIGNAL_CONTEXT"

    for rule in SIGNAL_CLASS_RULES:
        for pattern in rule.patterns:
            if pattern.lower() in haystack:
                return rule.signal_class

    return "UNCLASSIFIED_SIGNAL"


def signal_family(symbol: str, continuous_symbol: str) -> str:
    value = f"{symbol} {continuous_symbol}".upper()

    if "BR" in value or "BRENT" in value:
        return "ENERGY_OIL"
    if "GDU" in value or "GOLD" in value:
        return "METALS_GOLD"
    if "USDRUB" in value or "USD" in value:
        return "FX_USDRUB"
    if "NG" in value:
        return "ENERGY_GAS"
    if "@MISX" in value:
        return "EQUITY_MISX"

    return "OTHER"


def timeframe_bucket(timeframe: str) -> str:
    tf = _text(timeframe).upper()

    if tf in {"M1", "1M"}:
        return "EXECUTION_FAST_M1"
    if tf in {"M5", "5M"}:
        return "INTRADAY_SIGNAL_M5"
    if tf in {"M15", "15M"}:
        return "INTRADAY_CONFIRMATION_M15"
    if tf in {"H1", "1H"}:
        return "CONTEXT_H1"
    if tf in {"D1", "1D"}:
        return "BACKGROUND_D1"
    if tf == "LIVE":
        return "LIVE_RUNTIME"
    if not tf:
        return "TIMEFRAME_MISSING"

    return "TIMEFRAME_OTHER"


def side_sign(side: str) -> int:
    normalized = _text(side).upper()
    if normalized == "BUY":
        return 1
    if normalized == "SELL":
        return -1
    return 0


def trade_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _text(row.get("strategy")) or "UNKNOWN",
        _text(row.get("timeframe")) or "UNKNOWN",
        _text(row.get("continuous_symbol")) or _text(row.get("symbol")) or "UNKNOWN",
        _text(row.get("symbol")) or "UNKNOWN",
    )


def edge_status(closed_pairs: int, net_pnl: float, net_pnl_per_pair: float) -> str:
    if closed_pairs <= 0:
        return "NO_CLOSED_PAIRS"
    if net_pnl > 0 and net_pnl_per_pair > 0:
        return "EDGE_POSITIVE"
    if net_pnl < 0:
        if abs(net_pnl_per_pair) < 0.005:
            return "EDGE_FLAT_OR_WEAK"
        return "EDGE_NEGATIVE"
    return "EDGE_FLAT_OR_WEAK"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    lookback = os.getenv("SIGNAL_CLASS_EDGE_LOOKBACK", "30 days")
    limit = int(os.getenv("SIGNAL_CLASS_EDGE_LIMIT", "50000"))

    print("=== SIGNAL CLASS EDGE SCORECARD V1.1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print(f"lookback={lookback}")
    print(f"limit={limit}")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(TRADES_SQL, (lookback, limit))
            rows = [dict(r) for r in cur.fetchall()]

    rows_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_key.setdefault(trade_key(row), []).append(row)

    scorecard: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]] = {}
    open_tail_groups = 0
    total_open_qty = 0.0
    closed_pair_total = 0

    for key, group_rows in rows_by_key.items():
        # Русский комментарий:
        # FIFO stack хранит открытые ноги. Для текущей модели достаточно поштучного qty.
        open_lots: list[dict[str, Any]] = []

        for row in group_rows:
            qty = abs(_float(row.get("qty")))
            sign = side_sign(_text(row.get("side")))
            if sign == 0 or qty <= 0:
                continue

            remaining = qty

            while remaining > 1e-12 and open_lots and open_lots[0]["sign"] != sign:
                lot = open_lots[0]
                matched_qty = min(remaining, lot["remaining_qty"])

                entry = lot["row"]
                exit_row = row

                entry_sign = lot["sign"]
                entry_price = _float(entry.get("price"))
                exit_price = _float(exit_row.get("price"))

                # Русский комментарий:
                # BUY entry: pnl = exit - entry.
                # SELL entry: pnl = entry - exit.
                gross_pnl = (exit_price - entry_price) * matched_qty * entry_sign

                entry_commission = _float(entry.get("commission")) * (matched_qty / max(_float(entry.get("qty")), 1e-12))
                exit_commission = _float(exit_row.get("commission")) * (matched_qty / max(_float(exit_row.get("qty")), 1e-12))
                commission = entry_commission + exit_commission
                net_pnl = gross_pnl - commission

                entry_signal_class = classify_signal(entry)
                exit_signal_class = classify_signal(exit_row)

                strategy, timeframe, continuous_symbol, symbol = key
                family = signal_family(symbol, continuous_symbol)
                tf_bucket = timeframe_bucket(timeframe)

                sc_key = (
                    entry_signal_class,
                    exit_signal_class,
                    family,
                    strategy,
                    timeframe,
                    continuous_symbol,
                    symbol,
                )

                item = scorecard.setdefault(
                    sc_key,
                    {
                        "entry_signal_class": entry_signal_class,
                        "exit_signal_class": exit_signal_class,
                        "family": family,
                        "strategy": strategy,
                        "timeframe": timeframe,
                        "timeframe_bucket": tf_bucket,
                        "continuous_symbol": continuous_symbol,
                        "symbol": symbol,
                        "closed_pairs": 0,
                        "closed_qty": 0.0,
                        "gross_pnl": 0.0,
                        "commission": 0.0,
                        "net_pnl": 0.0,
                        "first_entry": None,
                        "last_exit": None,
                    },
                )

                item["closed_pairs"] += 1
                item["closed_qty"] += matched_qty
                item["gross_pnl"] += gross_pnl
                item["commission"] += commission
                item["net_pnl"] += net_pnl

                entry_ts = entry.get("created_at")
                exit_ts = exit_row.get("created_at")
                if item["first_entry"] is None or entry_ts < item["first_entry"]:
                    item["first_entry"] = entry_ts
                if item["last_exit"] is None or exit_ts > item["last_exit"]:
                    item["last_exit"] = exit_ts

                closed_pair_total += 1

                lot["remaining_qty"] -= matched_qty
                remaining -= matched_qty

                if lot["remaining_qty"] <= 1e-12:
                    open_lots.pop(0)

            if remaining > 1e-12:
                open_lots.append(
                    {
                        "row": row,
                        "sign": sign,
                        "remaining_qty": remaining,
                    }
                )

        open_qty = sum(float(lot["remaining_qty"]) for lot in open_lots)
        if open_qty > 1e-12:
            open_tail_groups += 1
            total_open_qty += open_qty

    items = []
    for item in scorecard.values():
        closed_pairs = int(item["closed_pairs"])
        net_pnl_per_pair = item["net_pnl"] / closed_pairs if closed_pairs else 0.0
        gross_pnl_per_pair = item["gross_pnl"] / closed_pairs if closed_pairs else 0.0
        commission_drag = abs(item["commission"] / item["gross_pnl"]) if abs(item["gross_pnl"]) > 1e-12 else None

        item["net_pnl_per_pair"] = net_pnl_per_pair
        item["gross_pnl_per_pair"] = gross_pnl_per_pair
        item["commission_drag"] = commission_drag
        item["edge_status"] = edge_status(closed_pairs, item["net_pnl"], net_pnl_per_pair)
        items.append(item)

    sorted_items = sorted(
        items,
        key=lambda x: (
            x["edge_status"] != "EDGE_POSITIVE",
            -abs(float(x["net_pnl"])),
            -int(x["closed_pairs"]),
            x["entry_signal_class"],
            x["exit_signal_class"],
            x["strategy"],
        ),
    )

    print()
    print("SIGNAL_CLASS_EDGE_SCORECARD_V1_1_ROWS")
    for item in sorted_items:
        commission_drag = item["commission_drag"]
        commission_drag_text = "None" if commission_drag is None else f"{commission_drag:.6f}"

        print(
            "SIGNAL_CLASS_EDGE_V1_1_ROW "
            f"entry_signal_class={item['entry_signal_class']} "
            f"exit_signal_class={item['exit_signal_class']} "
            f"family={item['family']} "
            f"strategy={item['strategy']} "
            f"timeframe={item['timeframe']} "
            f"timeframe_bucket={item['timeframe_bucket']} "
            f"continuous_symbol={item['continuous_symbol']} "
            f"symbol={item['symbol']} "
            f"closed_pairs={item['closed_pairs']} "
            f"closed_qty={item['closed_qty']:.4f} "
            f"gross_pnl={item['gross_pnl']:.6f} "
            f"commission={item['commission']:.6f} "
            f"net_pnl={item['net_pnl']:.6f} "
            f"gross_pnl_per_pair={item['gross_pnl_per_pair']:.6f} "
            f"net_pnl_per_pair={item['net_pnl_per_pair']:.6f} "
            f"commission_drag={commission_drag_text} "
            f"edge_status={item['edge_status']} "
            f"first_entry={item['first_entry']} "
            f"last_exit={item['last_exit']}"
        )

    total_rows = len(sorted_items)
    positive_rows = sum(1 for item in sorted_items if item["edge_status"] == "EDGE_POSITIVE")
    negative_rows = sum(1 for item in sorted_items if item["edge_status"] == "EDGE_NEGATIVE")
    weak_rows = sum(1 for item in sorted_items if item["edge_status"] == "EDGE_FLAT_OR_WEAK")
    unclassified_rows = sum(
        1
        for item in sorted_items
        if item["entry_signal_class"] in {"UNCLASSIFIED_SIGNAL", "NO_SIGNAL_CONTEXT"}
        or item["exit_signal_class"] in {"UNCLASSIFIED_SIGNAL", "NO_SIGNAL_CONTEXT"}
    )

    total_net_pnl = sum(float(item["net_pnl"]) for item in sorted_items)
    total_gross_pnl = sum(float(item["gross_pnl"]) for item in sorted_items)
    total_commission = sum(float(item["commission"]) for item in sorted_items)

    print()
    print("SIGNAL_CLASS_EDGE_SCORECARD_V1_1_SUMMARY")
    print(f"rows_total={total_rows}")
    print(f"closed_pairs_total={closed_pair_total}")
    print(f"positive_rows={positive_rows}")
    print(f"negative_rows={negative_rows}")
    print(f"weak_rows={weak_rows}")
    print(f"unclassified_rows={unclassified_rows}")
    print(f"open_tail_groups={open_tail_groups}")
    print(f"total_open_qty={total_open_qty:.4f}")
    print(f"total_gross_pnl={total_gross_pnl:.6f}")
    print(f"total_commission={total_commission:.6f}")
    print(f"total_net_pnl={total_net_pnl:.6f}")

    if total_rows == 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_SCORECARD_V1_1_EMPTY")
    elif positive_rows == 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_SCORECARD_V1_1_NO_POSITIVE_EDGE")
    elif unclassified_rows > 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_SCORECARD_V1_1_HAS_POSITIVE_AND_UNCLASSIFIED")
    else:
        print("VERDICT=SIGNAL_CLASS_EDGE_SCORECARD_V1_1_READY")

    print("SIGNAL_CLASS_EDGE_SCORECARD_V1_1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
