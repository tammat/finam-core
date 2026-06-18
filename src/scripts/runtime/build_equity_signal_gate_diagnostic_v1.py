#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_SIGNAL_GATE_DIAGNOSTIC_V1_PG_PERCENT_ESCAPE_V2
# Русский комментарий: все SQL LIKE-шаблоны с % экранируются как %% для psycopg2.
# EQUITY_SIGNAL_GATE_DIAGNOSTIC_V1 — read-only диагностика,
# почему equity symbols есть в runtime_active_universe, но не дают trades.
# Ничего не меняет в БД, runtime, systemd и execution.


RUNTIME_EQUITY_SQL = """
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
    last_seen_at,
    updated_at,
    raw_json
FROM runtime_active_universe
WHERE symbol LIKE '%%@MISX'
ORDER BY is_enabled DESC, priority DESC NULLS LAST, score DESC NULLS LAST, symbol;
"""


TRADE_EQUITY_SQL = """
SELECT
    symbol,
    COALESCE(strategy, 'UNKNOWN') AS strategy,
    COALESCE(timeframe, 'UNKNOWN') AS timeframe,
    COUNT(*) AS trades,
    MIN(created_at) AS first_trade,
    MAX(created_at) AS last_trade
FROM trades
WHERE created_at >= now() - (%s::text)::interval
  AND symbol LIKE '%%@MISX'
  AND COALESCE(is_invalid, false) = false
GROUP BY symbol, strategy, timeframe
ORDER BY trades DESC, symbol;
"""


BARS_EQUITY_SQL = """
SELECT
    symbol,
    timeframe,
    COUNT(*) AS bars,
    MIN(ts) AS first_bar,
    MAX(ts) AS last_bar
FROM market_bars
WHERE ts >= now() - (%s::text)::interval
  AND symbol LIKE '%%@MISX'
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def raw_get(raw_json: Any, *keys: str) -> str:
    if not isinstance(raw_json, dict):
        return ""

    for key in keys:
        value = raw_json.get(key)
        if value is not None:
            return str(value)

    return ""


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    lookback = os.getenv("EQUITY_SIGNAL_GATE_LOOKBACK", "24 hours")

    print("=== EQUITY SIGNAL GATE DIAGNOSTIC V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback={lookback}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_EQUITY_SQL)
            runtime_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(TRADE_EQUITY_SQL, (lookback,))
            trade_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(BARS_EQUITY_SQL, (lookback,))
            bar_rows = [dict(r) for r in cur.fetchall()]

    trade_by_symbol = {norm(r.get("symbol")): r for r in trade_rows}

    bars_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in bar_rows:
        bars_by_symbol.setdefault(norm(row.get("symbol")), []).append(row)

    enabled_equities = 0
    equities_with_bars = 0
    equities_with_trades = 0
    equities_enabled_with_bars_no_trades = 0

    print("EQUITY_SIGNAL_GATE_ROWS")

    for row in runtime_rows:
        symbol = norm(row.get("symbol"))
        enabled = bool(row.get("is_enabled"))
        bars = bars_by_symbol.get(symbol, [])
        trade = trade_by_symbol.get(symbol)

        has_bars = len(bars) > 0
        has_trades = trade is not None

        if enabled:
            enabled_equities += 1
        if has_bars:
            equities_with_bars += 1
        if has_trades:
            equities_with_trades += 1
        if enabled and has_bars and not has_trades:
            equities_enabled_with_bars_no_trades += 1

        raw_json = row.get("raw_json")
        gate_reason = (
            norm(row.get("disable_reason"))
            or raw_get(raw_json, "gate_reason", "filter_reason", "reason", "status")
            or "NONE"
        )

        if not enabled:
            diagnosis = "DISABLED_IN_RUNTIME"
        elif not has_bars:
            diagnosis = "ENABLED_BUT_NO_MARKET_BARS"
        elif not has_trades:
            diagnosis = "ENABLED_WITH_BARS_BUT_NO_TRADES"
        else:
            diagnosis = "EQUITY_TRADES_ACCUMULATING"

        print(
            "EQUITY_SIGNAL_GATE_ROW "
            f"symbol={symbol} "
            f"strategy={norm(row.get('strategy')) or 'UNKNOWN'} "
            f"timeframe={norm(row.get('timeframe')) or 'UNKNOWN'} "
            f"score={row.get('score')} "
            f"priority={row.get('priority')} "
            f"is_enabled={enabled} "
            f"has_bars={1 if has_bars else 0} "
            f"has_trades={1 if has_trades else 0} "
            f"bars_timeframes={','.join(sorted({norm(b.get('timeframe')) for b in bars})) if bars else 'NONE'} "
            f"last_bar={max((b.get('last_bar') for b in bars), default=None)} "
            f"trade_count={trade.get('trades') if trade else 0} "
            f"last_trade={trade.get('last_trade') if trade else None} "
            f"gate_reason={gate_reason} "
            f"diagnosis={diagnosis}"
        )

    print()
    print("EQUITY_SIGNAL_GATE_DIAGNOSTIC_SUMMARY")
    print(f"runtime_equity_rows={len(runtime_rows)}")
    print(f"enabled_equities={enabled_equities}")
    print(f"equities_with_bars={equities_with_bars}")
    print(f"equities_with_trades={equities_with_trades}")
    print(f"equities_enabled_with_bars_no_trades={equities_enabled_with_bars_no_trades}")
    print("db_update=0")

    if len(runtime_rows) == 0:
        print("VERDICT=EQUITY_SIGNAL_GATE_NO_RUNTIME_EQUITIES")
    elif equities_enabled_with_bars_no_trades > 0:
        print("VERDICT=EQUITY_SIGNAL_GATE_ENABLED_WITH_BARS_BUT_NO_TRADES")
    elif equities_with_trades > 0:
        print("VERDICT=EQUITY_SIGNAL_GATE_TRADES_ACCUMULATING")
    else:
        print("VERDICT=EQUITY_SIGNAL_GATE_NEEDS_ROUTE_REVIEW")

    print("EQUITY_SIGNAL_GATE_DIAGNOSTIC_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
