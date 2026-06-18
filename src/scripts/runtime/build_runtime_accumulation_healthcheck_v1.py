#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# RUNTIME_ACCUMULATION_HEALTHCHECK_V1 — read-only проверка накопления данных.
# Ничего не меняет в БД, runtime_active_universe, systemd и execution.
# Цель — понять, копятся ли trades/fills, чистый ли trade context,
# какие инструменты есть в runtime_active_universe и почему акции не доходят до тестов.


RUNTIME_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    regime,
    score,
    priority,
    is_enabled,
    disable_reason,
    source,
    allocated_at,
    last_seen_at,
    updated_at,
    raw_json
FROM runtime_active_universe
ORDER BY is_enabled DESC, priority DESC NULLS LAST, score DESC NULLS LAST, symbol;
"""


TRADE_TODAY_SQL = """
SELECT
    COUNT(*) AS trades_today,
    COUNT(*) FILTER (WHERE COALESCE(strategy, '') = '') AS strategy_missing_today,
    COUNT(*) FILTER (WHERE COALESCE(timeframe, '') = '') AS timeframe_missing_today,
    COUNT(*) FILTER (WHERE COALESCE(continuous_symbol, '') = '') AS continuous_symbol_missing_today,
    MIN(created_at) AS first_trade,
    MAX(created_at) AS last_trade
FROM trades
WHERE created_at::date = (now() AT TIME ZONE 'UTC')::date
  AND COALESCE(is_invalid, false) = false;
"""


TRADE_BY_SYMBOL_SQL = """
SELECT
    symbol,
    COALESCE(strategy, 'UNKNOWN') AS strategy,
    COALESCE(timeframe, 'UNKNOWN') AS timeframe,
    COALESCE(continuous_symbol, 'UNKNOWN') AS continuous_symbol,
    COUNT(*) AS trades,
    MIN(created_at) AS first_trade,
    MAX(created_at) AS last_trade
FROM trades
WHERE created_at >= now() - (%s::text)::interval
  AND COALESCE(is_invalid, false) = false
GROUP BY symbol, strategy, timeframe, continuous_symbol
ORDER BY trades DESC, symbol
LIMIT %s;
"""


DISCOVERY_SQL = """
SELECT
    COUNT(*) AS discovery_total,
    COUNT(*) FILTER (WHERE status = 'NEW') AS discovery_new,
    COUNT(*) FILTER (WHERE status = 'TEST_CLOSED') AS discovery_test_closed
FROM signal_strategy_discovery_events;
"""


MARKET_BARS_SQL = """
SELECT
    symbol,
    timeframe,
    COUNT(*) AS bars,
    MIN(ts) AS first_bar,
    MAX(ts) AS last_bar
FROM market_bars
WHERE ts >= now() - (%s::text)::interval
GROUP BY symbol, timeframe
ORDER BY MAX(ts) DESC, symbol, timeframe
LIMIT %s;
"""


def normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def asset_class(symbol: str) -> str:
    upper = symbol.upper()

    if "@MISX" in upper:
        return "EQUITY_MISX"
    if "USDRUB" in upper or "USD" in upper:
        return "FX_USDRUB"
    if upper.startswith("BR") or "BRENT" in upper:
        return "ENERGY_OIL"
    if upper.startswith("NG"):
        return "ENERGY_GAS"
    if upper.startswith("GDU") or "GOLD" in upper:
        return "METALS_GOLD"

    return "OTHER"


def raw_reason(raw_json: Any) -> str:
    if not isinstance(raw_json, dict):
        return ""

    for key in (
        "reason",
        "disable_reason",
        "filter_reason",
        "gate_reason",
        "selection_reason",
        "allocation_reason",
        "status",
    ):
        value = raw_json.get(key)
        if value is not None:
            return str(value)

    return ""


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    lookback = os.getenv("RUNTIME_ACCUMULATION_LOOKBACK", "24 hours")
    limit = int(os.getenv("RUNTIME_ACCUMULATION_LIMIT", "100"))

    print("=== RUNTIME ACCUMULATION HEALTHCHECK V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback={lookback}")
    print(f"limit={limit}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_SQL)
            runtime_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(TRADE_TODAY_SQL)
            trade_today = dict(cur.fetchone() or {})

            cur.execute(TRADE_BY_SYMBOL_SQL, (lookback, limit))
            trade_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(DISCOVERY_SQL)
            discovery = dict(cur.fetchone() or {})

            try:
                cur.execute(MARKET_BARS_SQL, (lookback, limit))
                bar_rows = [dict(r) for r in cur.fetchall()]
                market_bars_available = True
            except Exception as exc:
                bar_rows = []
                market_bars_available = False
                print(f"MARKET_BARS_QUERY_WARN error={type(exc).__name__}:{exc}")

    runtime_enabled = 0
    runtime_disabled = 0
    runtime_equities = 0
    runtime_equities_enabled = 0
    runtime_futures = 0

    print("RUNTIME_ACTIVE_UNIVERSE_ROWS")
    for row in runtime_rows:
        symbol = normalize(row.get("symbol"))
        cls = asset_class(symbol)
        enabled = bool(row.get("is_enabled"))
        reason = normalize(row.get("disable_reason")) or raw_reason(row.get("raw_json")) or "NONE"

        if enabled:
            runtime_enabled += 1
        else:
            runtime_disabled += 1

        if cls == "EQUITY_MISX":
            runtime_equities += 1
            if enabled:
                runtime_equities_enabled += 1
        else:
            runtime_futures += 1

        print(
            "RUNTIME_ACTIVE_UNIVERSE_ROW "
            f"symbol={symbol} "
            f"asset_class={cls} "
            f"strategy={normalize(row.get('strategy')) or 'UNKNOWN'} "
            f"timeframe={normalize(row.get('timeframe')) or 'UNKNOWN'} "
            f"score={row.get('score')} "
            f"priority={row.get('priority')} "
            f"is_enabled={enabled} "
            f"disable_reason={reason} "
            f"source={normalize(row.get('source')) or 'UNKNOWN'} "
            f"last_seen_at={row.get('last_seen_at')} "
            f"updated_at={row.get('updated_at')}"
        )

    print()
    print("TRADE_ACCUMULATION_TODAY")
    print(f"trades_today={trade_today.get('trades_today', 0)}")
    print(f"strategy_missing_today={trade_today.get('strategy_missing_today', 0)}")
    print(f"timeframe_missing_today={trade_today.get('timeframe_missing_today', 0)}")
    print(f"continuous_symbol_missing_today={trade_today.get('continuous_symbol_missing_today', 0)}")
    print(f"first_trade={trade_today.get('first_trade')}")
    print(f"last_trade={trade_today.get('last_trade')}")

    equity_trade_rows = 0
    futures_trade_rows = 0

    print()
    print("TRADE_ACCUMULATION_BY_SYMBOL")
    for row in trade_rows:
        symbol = normalize(row.get("symbol"))
        cls = asset_class(symbol)

        if cls == "EQUITY_MISX":
            equity_trade_rows += 1
        else:
            futures_trade_rows += 1

        print(
            "TRADE_ACCUMULATION_SYMBOL_ROW "
            f"symbol={symbol} "
            f"asset_class={cls} "
            f"strategy={normalize(row.get('strategy')) or 'UNKNOWN'} "
            f"timeframe={normalize(row.get('timeframe')) or 'UNKNOWN'} "
            f"continuous_symbol={normalize(row.get('continuous_symbol')) or 'UNKNOWN'} "
            f"trades={row.get('trades')} "
            f"first_trade={row.get('first_trade')} "
            f"last_trade={row.get('last_trade')}"
        )

    print()
    print("SIGNAL_DISCOVERY_HEALTH")
    print(f"discovery_total={discovery.get('discovery_total', 0)}")
    print(f"discovery_new={discovery.get('discovery_new', 0)}")
    print(f"discovery_test_closed={discovery.get('discovery_test_closed', 0)}")

    market_bar_equities = 0
    market_bar_futures = 0

    print()
    print("MARKET_BARS_FRESHNESS")
    print(f"market_bars_available={1 if market_bars_available else 0}")
    for row in bar_rows:
        symbol = normalize(row.get("symbol"))
        cls = asset_class(symbol)

        if cls == "EQUITY_MISX":
            market_bar_equities += 1
        else:
            market_bar_futures += 1

        print(
            "MARKET_BARS_FRESHNESS_ROW "
            f"symbol={symbol} "
            f"asset_class={cls} "
            f"timeframe={normalize(row.get('timeframe')) or 'UNKNOWN'} "
            f"bars={row.get('bars')} "
            f"first_bar={row.get('first_bar')} "
            f"last_bar={row.get('last_bar')}"
        )

    failures = 0

    trades_today = int(trade_today.get("trades_today") or 0)
    strategy_missing = int(trade_today.get("strategy_missing_today") or 0)
    timeframe_missing = int(trade_today.get("timeframe_missing_today") or 0)
    continuous_missing = int(trade_today.get("continuous_symbol_missing_today") or 0)
    discovery_new = int(discovery.get("discovery_new") or 0)

    if trades_today <= 0:
        failures += 1
    if strategy_missing != 0 or timeframe_missing != 0 or continuous_missing != 0:
        failures += 1
    if discovery_new != 0:
        failures += 1

    equity_reason = "OK"
    if runtime_equities == 0 and equity_trade_rows == 0:
        equity_reason = "NO_EQUITIES_IN_RUNTIME_OR_TRADES"
    elif runtime_equities > 0 and runtime_equities_enabled == 0:
        equity_reason = "EQUITIES_PRESENT_BUT_DISABLED"
    elif runtime_equities_enabled > 0 and equity_trade_rows == 0:
        equity_reason = "EQUITIES_ENABLED_BUT_NO_TRADES"
    elif equity_trade_rows > 0:
        equity_reason = "EQUITY_TRADES_ACCUMULATING"

    print()
    print("RUNTIME_ACCUMULATION_HEALTHCHECK_SUMMARY")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"runtime_enabled={runtime_enabled}")
    print(f"runtime_disabled={runtime_disabled}")
    print(f"runtime_equities={runtime_equities}")
    print(f"runtime_equities_enabled={runtime_equities_enabled}")
    print(f"runtime_non_equities={runtime_futures}")
    print(f"trade_rows={len(trade_rows)}")
    print(f"equity_trade_rows={equity_trade_rows}")
    print(f"non_equity_trade_rows={futures_trade_rows}")
    print(f"market_bar_equity_rows={market_bar_equities}")
    print(f"market_bar_non_equity_rows={market_bar_futures}")
    print(f"trades_today={trades_today}")
    print(f"trade_context_failures={1 if strategy_missing or timeframe_missing or continuous_missing else 0}")
    print(f"discovery_new={discovery_new}")
    print(f"equity_accumulation_reason={equity_reason}")
    print(f"failures={failures}")
    print("db_update=0")

    if failures > 0:
        print("VERDICT=RUNTIME_ACCUMULATION_HEALTHCHECK_HAS_FAILURES")
        print("RUNTIME_ACCUMULATION_HEALTHCHECK_V1_FAILED")
        return 1

    if equity_reason != "EQUITY_TRADES_ACCUMULATING":
        print("VERDICT=RUNTIME_ACCUMULATION_HEALTHCHECK_OK_EQUITIES_NOT_ACCUMULATING")
    else:
        print("VERDICT=RUNTIME_ACCUMULATION_HEALTHCHECK_OK")

    print("RUNTIME_ACCUMULATION_HEALTHCHECK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
