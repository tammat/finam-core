#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_STRATEGY_INTENT_FLOW_DIAGNOSTIC_V1 — read-only диагностика equity-flow.
# Цель: понять, почему SBER@MISX имеет runtime row и market_bars,
# но не даёт signal/intent/trade.
# Скрипт ничего не меняет в БД, runtime, systemd и execution.


RUNTIME_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    score,
    priority,
    is_enabled,
    disable_reason,
    source,
    raw_json,
    last_seen_at,
    updated_at
FROM runtime_active_universe
WHERE symbol = %s
ORDER BY updated_at DESC
LIMIT 5;
"""


BARS_SQL = """
SELECT
    symbol,
    timeframe,
    COUNT(*) AS bars,
    MIN(ts) AS first_bar,
    MAX(ts) AS last_bar,
    MIN(close) AS min_close,
    MAX(close) AS max_close,
    AVG(close) AS avg_close
FROM market_bars
WHERE symbol = %s
  AND ts >= now() - (%s::text)::interval
GROUP BY symbol, timeframe
ORDER BY timeframe;
"""


LAST_BARS_SQL = """
SELECT
    symbol,
    timeframe,
    ts,
    open,
    high,
    low,
    close,
    volume
FROM market_bars
WHERE symbol = %s
  AND timeframe = %s
ORDER BY ts DESC
LIMIT %s;
"""


TRADES_SQL = """
SELECT
    id,
    symbol,
    side,
    qty,
    price,
    strategy,
    timeframe,
    continuous_symbol,
    created_at,
    payload
FROM trades
WHERE symbol = %s
  AND created_at >= now() - (%s::text)::interval
  AND COALESCE(is_invalid, false) = false
ORDER BY created_at DESC
LIMIT 20;
"""


SIGNAL_TABLES_SQL = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (
       table_name ILIKE '%%signal%%'
    OR table_name ILIKE '%%intent%%'
    OR table_name ILIKE '%%event%%'
  )
ORDER BY table_name;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def classify_bar_status(rows: list[dict[str, Any]], timeframe: str) -> tuple[int, str, str]:
    filtered = [r for r in rows if norm(r.get("timeframe")) == timeframe]
    if not filtered:
        return 0, "NO_BARS", "no_bars_for_required_timeframe"

    row = filtered[0]
    bars = int(row.get("bars") or 0)

    if bars < 20:
        return bars, "INSUFFICIENT_BARS", "less_than_20_bars"

    min_close = to_float(row.get("min_close"))
    max_close = to_float(row.get("max_close"))

    if min_close <= 0 or max_close <= 0:
        return bars, "BAD_PRICE_DATA", "non_positive_close"

    if abs(max_close - min_close) < 1e-12:
        return bars, "FLAT_PRICE_DATA", "no_price_range"

    return bars, "BARS_OK", "bars_available"


def compute_simple_volatility(last_bars: list[dict[str, Any]]) -> tuple[float, float, str]:
    if len(last_bars) < 20:
        return 0.0, 0.0, "insufficient_bars_for_volatility"

    closes = [to_float(r.get("close")) for r in reversed(last_bars)]
    highs = [to_float(r.get("high")) for r in reversed(last_bars)]
    lows = [to_float(r.get("low")) for r in reversed(last_bars)]

    if any(x <= 0 for x in closes):
        return 0.0, 0.0, "bad_close_values"

    returns = []
    for prev, cur in zip(closes, closes[1:]):
        if prev > 0:
            returns.append((cur - prev) / prev)

    avg_abs_return = sum(abs(r) for r in returns) / len(returns) if returns else 0.0
    avg_range_pct = sum((h - l) / c for h, l, c in zip(highs, lows, closes) if c > 0) / len(closes)

    if avg_abs_return <= 0 and avg_range_pct <= 0:
        return avg_abs_return, avg_range_pct, "flat_market"

    return avg_abs_return, avg_range_pct, "volatility_available"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    symbol = os.getenv("EQUITY_INTENT_SYMBOL", "SBER@MISX")
    lookback = os.getenv("EQUITY_INTENT_LOOKBACK", "24 hours")
    required_timeframe = os.getenv("EQUITY_INTENT_TIMEFRAME", "M5")
    last_limit = int(os.getenv("EQUITY_INTENT_LAST_BARS", "60"))

    print("=== EQUITY STRATEGY INTENT FLOW DIAGNOSTIC V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={symbol}")
    print(f"lookback={lookback}")
    print(f"required_timeframe={required_timeframe}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_SQL, (symbol,))
            runtime_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(BARS_SQL, (symbol, lookback))
            bar_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(LAST_BARS_SQL, (symbol, required_timeframe, last_limit))
            last_bars = [dict(r) for r in cur.fetchall()]

            cur.execute(TRADES_SQL, (symbol, lookback))
            trade_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(SIGNAL_TABLES_SQL)
            signal_tables = [dict(r) for r in cur.fetchall()]

    print("EQUITY_INTENT_RUNTIME_ROWS")
    for row in runtime_rows:
        print(
            "EQUITY_INTENT_RUNTIME_ROW "
            f"symbol={norm(row.get('symbol'))} "
            f"strategy={norm(row.get('strategy')) or 'UNKNOWN'} "
            f"timeframe={norm(row.get('timeframe')) or 'UNKNOWN'} "
            f"score={row.get('score')} "
            f"priority={row.get('priority')} "
            f"is_enabled={bool(row.get('is_enabled'))} "
            f"disable_reason={norm(row.get('disable_reason')) or 'NONE'} "
            f"source={norm(row.get('source')) or 'UNKNOWN'} "
            f"last_seen_at={row.get('last_seen_at')} "
            f"updated_at={row.get('updated_at')}"
        )

    print()
    print("EQUITY_INTENT_MARKET_BARS")
    for row in bar_rows:
        print(
            "EQUITY_INTENT_MARKET_BARS_ROW "
            f"symbol={norm(row.get('symbol'))} "
            f"timeframe={norm(row.get('timeframe'))} "
            f"bars={row.get('bars')} "
            f"first_bar={row.get('first_bar')} "
            f"last_bar={row.get('last_bar')} "
            f"min_close={row.get('min_close')} "
            f"max_close={row.get('max_close')} "
            f"avg_close={row.get('avg_close')}"
        )

    required_bars, bar_status, bar_reason = classify_bar_status(bar_rows, required_timeframe)
    avg_abs_return, avg_range_pct, volatility_reason = compute_simple_volatility(last_bars)

    print()
    print("EQUITY_INTENT_FEATURE_PROXY")
    print(f"required_timeframe={required_timeframe}")
    print(f"required_bars={required_bars}")
    print(f"bar_status={bar_status}")
    print(f"bar_reason={bar_reason}")
    print(f"last_bars_loaded={len(last_bars)}")
    print(f"avg_abs_return={avg_abs_return:.8f}")
    print(f"avg_range_pct={avg_range_pct:.8f}")
    print(f"volatility_reason={volatility_reason}")

    print()
    print("EQUITY_INTENT_TRADES")
    for row in trade_rows:
        print(
            "EQUITY_INTENT_TRADE_ROW "
            f"id={row.get('id')} "
            f"symbol={norm(row.get('symbol'))} "
            f"side={norm(row.get('side'))} "
            f"qty={row.get('qty')} "
            f"price={row.get('price')} "
            f"strategy={norm(row.get('strategy')) or 'UNKNOWN'} "
            f"timeframe={norm(row.get('timeframe')) or 'UNKNOWN'} "
            f"continuous_symbol={norm(row.get('continuous_symbol')) or 'UNKNOWN'} "
            f"created_at={row.get('created_at')}"
        )

    print()
    print("EQUITY_INTENT_SIGNAL_TABLE_DISCOVERY")
    for row in signal_tables:
        print(f"EQUITY_INTENT_SIGNAL_TABLE table={row.get('table_name')}")

    runtime_enabled = any(bool(r.get("is_enabled")) for r in runtime_rows)
    strategy = norm(runtime_rows[0].get("strategy")) if runtime_rows else "UNKNOWN"
    timeframe = norm(runtime_rows[0].get("timeframe")) if runtime_rows else "UNKNOWN"

    trades_count = len(trade_rows)

    if not runtime_rows:
        diagnosis = "NO_RUNTIME_ROW"
        next_step = "runtime_universe_route_review"
    elif not runtime_enabled:
        diagnosis = "RUNTIME_ROW_DISABLED"
        next_step = "runtime_enable_reason_review"
    elif bar_status != "BARS_OK":
        diagnosis = "MARKET_BARS_NOT_READY"
        next_step = "market_data_ingestion_or_timeframe_review"
    elif trades_count == 0:
        diagnosis = "BARS_OK_BUT_NO_TRADES"
        next_step = "strategy_intent_generation_review"
    else:
        diagnosis = "EQUITY_TRADES_ACCUMULATING"
        next_step = "no_action"

    print()
    print("EQUITY_STRATEGY_INTENT_FLOW_DIAGNOSTIC_SUMMARY")
    print(f"symbol={symbol}")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"runtime_enabled={1 if runtime_enabled else 0}")
    print(f"strategy={strategy}")
    print(f"timeframe={timeframe}")
    print(f"bar_status={bar_status}")
    print(f"required_bars={required_bars}")
    print(f"trades_count={trades_count}")
    print(f"diagnosis={diagnosis}")
    print(f"next_step={next_step}")
    print("db_update=0")

    if diagnosis == "BARS_OK_BUT_NO_TRADES":
        print("VERDICT=EQUITY_STRATEGY_INTENT_FLOW_BARS_OK_NO_TRADES")
    elif diagnosis == "EQUITY_TRADES_ACCUMULATING":
        print("VERDICT=EQUITY_STRATEGY_INTENT_FLOW_OK")
    else:
        print("VERDICT=EQUITY_STRATEGY_INTENT_FLOW_BLOCKED_BEFORE_TRADES")

    print("EQUITY_STRATEGY_INTENT_FLOW_DIAGNOSTIC_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
