#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


# Русский комментарий:
# SIGNAL_CLASS_EDGE_SCORECARD_V1 — read-only оценка edge по классам сигналов.
# Скрипт ничего не пишет в БД, не меняет runtime и не включает execution.
# Расчёт грубый: closed-chain на основе BUY/SELL qty и price внутри группы.
# Цель этапа — увидеть, какие классы сигналов вообще имеют положительный net edge.


@dataclass(frozen=True)
class SignalClassRule:
    signal_class: str
    patterns: tuple[str, ...]


SIGNAL_CLASS_RULES: tuple[SignalClassRule, ...] = (
    SignalClassRule("GOLD_SHORT_SHADOW", ("gold_short_only_shadow_v1",)),
    SignalClassRule("TIME_EXIT", ("time_exit", "timeout", "time_stop")),
    SignalClassRule("SMART_ENTRY_RETEST", ("smart_entry_retest", "retest")),
    SignalClassRule("BREAKOUT", ("breakout", "break_out", "range_break", "level_break")),
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
ORDER BY created_at, id
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

    # Русский комментарий:
    # Порядок важен: BR_ROLLING содержит подстроку "NG", поэтому BR проверяем раньше NG.
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


def direction_bucket(side: str, signal_class: str) -> str:
    normalized_side = _text(side).upper()

    if signal_class in {"TIME_EXIT", "REGIME_FILTER"}:
        return "EXIT"
    if normalized_side == "BUY":
        return "LONG_ENTRY_OR_COVER"
    if normalized_side == "SELL":
        return "SHORT_ENTRY_OR_EXIT"

    return "UNKNOWN_DIRECTION"


def edge_status(
    trades: int,
    net_qty: float,
    gross_pnl: float,
    commission: float,
    net_pnl: float,
    net_pnl_per_trade: float,
) -> str:
    if trades <= 0:
        return "NO_TRADES"

    if abs(net_qty) > 1e-9:
        return "OPEN_TAIL_REQUIRES_MTM"

    if net_pnl > 0 and net_pnl_per_trade > 0:
        return "EDGE_POSITIVE"

    if gross_pnl > 0 and net_pnl <= 0:
        return "EDGE_KILLED_BY_COMMISSION"

    if net_pnl < 0:
        if abs(net_pnl_per_trade) < 0.005:
            return "EDGE_FLAT_OR_WEAK"
        return "EDGE_NEGATIVE"

    return "EDGE_FLAT_OR_WEAK"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    lookback = os.getenv("SIGNAL_CLASS_EDGE_LOOKBACK", "30 days")
    limit = int(os.getenv("SIGNAL_CLASS_EDGE_LIMIT", "50000"))

    print("=== SIGNAL CLASS EDGE SCORECARD V1 ===")
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

    scorecard: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}

    for row in rows:
        signal_class = classify_signal(row)
        family = signal_family(_text(row.get("symbol")), _text(row.get("continuous_symbol")))
        strategy = _text(row.get("strategy")) or "UNKNOWN"
        timeframe = _text(row.get("timeframe")) or "UNKNOWN"
        continuous_symbol = _text(row.get("continuous_symbol")) or _text(row.get("symbol")) or "UNKNOWN"
        tf_bucket = timeframe_bucket(timeframe)
        direction = direction_bucket(_text(row.get("side")), signal_class)

        key = (
            signal_class,
            family,
            strategy,
            timeframe,
            continuous_symbol,
            direction,
        )

        item = scorecard.setdefault(
            key,
            {
                "signal_class": signal_class,
                "family": family,
                "strategy": strategy,
                "timeframe": timeframe,
                "timeframe_bucket": tf_bucket,
                "continuous_symbol": continuous_symbol,
                "direction": direction,
                "trades": 0,
                "buy_qty": 0.0,
                "sell_qty": 0.0,
                "buy_value": 0.0,
                "sell_value": 0.0,
                "commission": 0.0,
                "symbols": set(),
                "first_trade": None,
                "last_trade": None,
                "missing_reason": 0,
            },
        )

        qty = _float(row.get("qty"))
        price = _float(row.get("price"))
        commission = _float(row.get("commission"))
        side = _text(row.get("side")).upper()

        item["trades"] += 1
        item["commission"] += commission
        item["symbols"].add(_text(row.get("symbol")))

        if side == "BUY":
            item["buy_qty"] += qty
            item["buy_value"] += qty * price
        elif side == "SELL":
            item["sell_qty"] += qty
            item["sell_value"] += qty * price

        if not _text(row.get("signal_reason")):
            item["missing_reason"] += 1

        created_at = row.get("created_at")
        if item["first_trade"] is None or created_at < item["first_trade"]:
            item["first_trade"] = created_at
        if item["last_trade"] is None or created_at > item["last_trade"]:
            item["last_trade"] = created_at

    items = []
    for item in scorecard.values():
        gross_pnl = item["sell_value"] - item["buy_value"]
        net_pnl = gross_pnl - item["commission"]
        net_qty = item["buy_qty"] - item["sell_qty"]
        trades = int(item["trades"])
        net_pnl_per_trade = net_pnl / trades if trades else 0.0
        gross_pnl_per_trade = gross_pnl / trades if trades else 0.0
        commission_drag = abs(item["commission"] / gross_pnl) if abs(gross_pnl) > 1e-12 else None

        item["gross_pnl"] = gross_pnl
        item["net_pnl"] = net_pnl
        item["net_qty"] = net_qty
        item["gross_pnl_per_trade"] = gross_pnl_per_trade
        item["net_pnl_per_trade"] = net_pnl_per_trade
        item["commission_drag"] = commission_drag
        item["edge_status"] = edge_status(
            trades=trades,
            net_qty=net_qty,
            gross_pnl=gross_pnl,
            commission=item["commission"],
            net_pnl=net_pnl,
            net_pnl_per_trade=net_pnl_per_trade,
        )
        items.append(item)

    sorted_items = sorted(
        items,
        key=lambda x: (
            x["edge_status"] != "EDGE_POSITIVE",
            x["edge_status"] == "OPEN_TAIL_REQUIRES_MTM",
            -abs(float(x["net_pnl"])),
            -int(x["trades"]),
            x["signal_class"],
            x["strategy"],
        ),
    )

    print()
    print("SIGNAL_CLASS_EDGE_SCORECARD_ROWS")
    for item in sorted_items:
        symbols = ",".join(sorted(item["symbols"]))[:240]
        commission_drag = item["commission_drag"]
        commission_drag_text = "None" if commission_drag is None else f"{commission_drag:.6f}"

        print(
            "SIGNAL_CLASS_EDGE_ROW "
            f"signal_class={item['signal_class']} "
            f"family={item['family']} "
            f"strategy={item['strategy']} "
            f"timeframe={item['timeframe']} "
            f"timeframe_bucket={item['timeframe_bucket']} "
            f"continuous_symbol={item['continuous_symbol']} "
            f"direction={item['direction']} "
            f"symbols={symbols} "
            f"trades={item['trades']} "
            f"buy_qty={item['buy_qty']:.4f} "
            f"sell_qty={item['sell_qty']:.4f} "
            f"net_qty={item['net_qty']:.4f} "
            f"gross_pnl={item['gross_pnl']:.6f} "
            f"commission={item['commission']:.6f} "
            f"net_pnl={item['net_pnl']:.6f} "
            f"gross_pnl_per_trade={item['gross_pnl_per_trade']:.6f} "
            f"net_pnl_per_trade={item['net_pnl_per_trade']:.6f} "
            f"commission_drag={commission_drag_text} "
            f"missing_reason={item['missing_reason']} "
            f"edge_status={item['edge_status']} "
            f"first_trade={item['first_trade']} "
            f"last_trade={item['last_trade']}"
        )

    total_rows = len(sorted_items)
    total_trades = sum(int(item["trades"]) for item in sorted_items)
    positive_rows = sum(1 for item in sorted_items if item["edge_status"] == "EDGE_POSITIVE")
    negative_rows = sum(1 for item in sorted_items if item["edge_status"] == "EDGE_NEGATIVE")
    weak_rows = sum(1 for item in sorted_items if item["edge_status"] == "EDGE_FLAT_OR_WEAK")
    commission_killed_rows = sum(1 for item in sorted_items if item["edge_status"] == "EDGE_KILLED_BY_COMMISSION")
    open_tail_rows = sum(1 for item in sorted_items if item["edge_status"] == "OPEN_TAIL_REQUIRES_MTM")
    unclassified_rows = sum(1 for item in sorted_items if item["signal_class"] in {"UNCLASSIFIED_SIGNAL", "NO_SIGNAL_CONTEXT"})

    total_net_pnl = sum(float(item["net_pnl"]) for item in sorted_items)
    total_gross_pnl = sum(float(item["gross_pnl"]) for item in sorted_items)
    total_commission = sum(float(item["commission"]) for item in sorted_items)

    print()
    print("SIGNAL_CLASS_EDGE_SCORECARD_SUMMARY")
    print(f"rows_total={total_rows}")
    print(f"trades_total={total_trades}")
    print(f"positive_rows={positive_rows}")
    print(f"negative_rows={negative_rows}")
    print(f"weak_rows={weak_rows}")
    print(f"commission_killed_rows={commission_killed_rows}")
    print(f"open_tail_rows={open_tail_rows}")
    print(f"unclassified_rows={unclassified_rows}")
    print(f"total_gross_pnl={total_gross_pnl:.6f}")
    print(f"total_commission={total_commission:.6f}")
    print(f"total_net_pnl={total_net_pnl:.6f}")

    if total_rows == 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_SCORECARD_EMPTY")
    elif positive_rows == 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_NO_CONFIRMED_POSITIVE_EDGE")
    elif unclassified_rows > 0:
        print("VERDICT=SIGNAL_CLASS_EDGE_HAS_POSITIVE_AND_UNCLASSIFIED")
    else:
        print("VERDICT=SIGNAL_CLASS_EDGE_SCORECARD_READY")

    print("SIGNAL_CLASS_EDGE_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
