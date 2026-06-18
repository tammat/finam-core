#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


# Русский комментарий:
# MARKET_SIGNAL_CATALOG_V1 — read-only каталог фактических рыночных сигналов.
# Скрипт ничего не пишет в БД, не меняет runtime и не включает execution.
# Источник — trades.payload + колонки strategy/timeframe/continuous_symbol.


@dataclass(frozen=True)
class SignalClassRule:
    signal_class: str
    patterns: tuple[str, ...]


SIGNAL_CLASS_RULES: tuple[SignalClassRule, ...] = (
    # MARKET_SIGNAL_CATALOG_V1_1_FAMILY_AND_GOLD_SHADOW_FIX
    # Русский комментарий:
    # GOLD shadow-сигналы часто не имеют payload.reason, поэтому классифицируем их по strategy.
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
    SignalClassRule("REGIME_FILTER", ("regime", "trend_up", "trend_down", "flat")),
    SignalClassRule("CROSS_MARKET_CONFIRMATION", ("cross_market", "confirmation", "brent", "usd", "dxy")),
    SignalClassRule("LIQUIDITY_FILTER", ("liquidity", "spread", "slippage", "book")),
)


CATALOG_SQL = """
WITH base AS (
    SELECT
        id,
        symbol,
        side,
        qty,
        price,
        commission,
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
            NULLIF(payload->'trade_context_snapshot'->>'strategy', '')
        ) AS resolved_strategy,
        COALESCE(
            NULLIF(timeframe, ''),
            NULLIF(payload->>'timeframe', ''),
            NULLIF(payload->'metadata'->>'timeframe', ''),
            NULLIF(payload->'trade_context_snapshot'->>'timeframe', '')
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
ORDER BY created_at DESC, id DESC
LIMIT %s;
"""


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


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


def format_reason(reason: Any) -> str:
    value = _text(reason)
    if not value:
        return "NONE"
    return re.sub(r"\s+", "_", value)[:120]


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    lookback = os.getenv("MARKET_SIGNAL_CATALOG_LOOKBACK", "30 days")
    limit = int(os.getenv("MARKET_SIGNAL_CATALOG_LIMIT", "50000"))

    print("=== MARKET SIGNAL CATALOG V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print(f"lookback={lookback}")
    print(f"limit={limit}")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(CATALOG_SQL, (lookback, limit))
            rows = [dict(r) for r in cur.fetchall()]

    catalog: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    unknown_rows: list[dict[str, Any]] = []

    for row in rows:
        signal_class = classify_signal(row)
        family = signal_family(_text(row.get("symbol")), _text(row.get("continuous_symbol")))
        tf_bucket = timeframe_bucket(_text(row.get("timeframe")))

        key = (
            signal_class,
            family,
            _text(row.get("strategy")) or "UNKNOWN",
            _text(row.get("timeframe")) or "UNKNOWN",
            _text(row.get("continuous_symbol")) or _text(row.get("symbol")) or "UNKNOWN",
        )

        item = catalog.setdefault(
            key,
            {
                "signal_class": signal_class,
                "family": family,
                "strategy": key[2],
                "timeframe": key[3],
                "timeframe_bucket": tf_bucket,
                "continuous_symbol": key[4],
                "trades": 0,
                "buy_qty": 0.0,
                "sell_qty": 0.0,
                "symbols": set(),
                "reasons": set(),
                "first_seen": None,
                "last_seen": None,
                "missing_reason": 0,
            },
        )

        qty = float(row.get("qty") or 0)
        side = _text(row.get("side")).upper()

        item["trades"] += 1
        item["symbols"].add(_text(row.get("symbol")))
        item["reasons"].add(format_reason(row.get("signal_reason")))

        if side == "BUY":
            item["buy_qty"] += qty
        elif side == "SELL":
            item["sell_qty"] += qty

        if not _text(row.get("signal_reason")):
            item["missing_reason"] += 1

        created_at = row.get("created_at")
        if item["first_seen"] is None or created_at < item["first_seen"]:
            item["first_seen"] = created_at
        if item["last_seen"] is None or created_at > item["last_seen"]:
            item["last_seen"] = created_at

        if signal_class in {"UNCLASSIFIED_SIGNAL", "NO_SIGNAL_CONTEXT"} or key[2] == "UNKNOWN":
            unknown_rows.append(row | {"signal_class": signal_class, "family": family})

    sorted_items = sorted(
        catalog.values(),
        key=lambda x: (-int(x["trades"]), x["signal_class"], x["strategy"], x["timeframe"]),
    )

    print()
    print("MARKET_SIGNAL_CATALOG_ROWS")
    for item in sorted_items:
        reasons = ",".join(sorted(item["reasons"]))[:240]
        symbols = ",".join(sorted(item["symbols"]))[:240]

        print(
            "MARKET_SIGNAL_CATALOG_ROW "
            f"signal_class={item['signal_class']} "
            f"family={item['family']} "
            f"strategy={item['strategy']} "
            f"timeframe={item['timeframe']} "
            f"timeframe_bucket={item['timeframe_bucket']} "
            f"continuous_symbol={item['continuous_symbol']} "
            f"trades={item['trades']} "
            f"symbols={symbols} "
            f"buy_qty={item['buy_qty']:.4f} "
            f"sell_qty={item['sell_qty']:.4f} "
            f"missing_reason={item['missing_reason']} "
            f"first_seen={item['first_seen']} "
            f"last_seen={item['last_seen']} "
            f"example_reasons={reasons}"
        )

    print()
    print("MARKET_SIGNAL_UNCLASSIFIED_ROWS")
    for row in unknown_rows[:100]:
        print(
            "MARKET_SIGNAL_UNCLASSIFIED_ROW "
            f"id={row.get('id')} "
            f"symbol={row.get('symbol')} "
            f"family={row.get('family')} "
            f"signal_class={row.get('signal_class')} "
            f"strategy={row.get('strategy') or 'UNKNOWN'} "
            f"timeframe={row.get('timeframe') or 'UNKNOWN'} "
            f"continuous_symbol={row.get('continuous_symbol') or row.get('symbol')} "
            f"reason={format_reason(row.get('signal_reason'))} "
            f"created_at={row.get('created_at')}"
        )

    total_trades = sum(int(item["trades"]) for item in sorted_items)
    total_unknown = len(unknown_rows)

    print()
    print("MARKET_SIGNAL_CATALOG_SUMMARY")
    print(f"rows_total={len(sorted_items)}")
    print(f"trades_total={total_trades}")
    print(f"unknown_or_unclassified_rows={total_unknown}")

    if total_trades == 0:
        print("VERDICT=MARKET_SIGNAL_CATALOG_EMPTY")
    elif total_unknown > 0:
        print("VERDICT=MARKET_SIGNAL_CATALOG_HAS_UNCLASSIFIED")
    else:
        print("VERDICT=MARKET_SIGNAL_CATALOG_READY")

    print("MARKET_SIGNAL_CATALOG_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
