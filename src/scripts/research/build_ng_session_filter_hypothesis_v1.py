#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


# Русский комментарий:
# NG_SESSION_FILTER_HYPOTHESIS_V1 — read-only проверка гипотезы:
# есть ли у smart_entry_retest по газу устойчивое улучшение в отдельных сессиях.
# Анализ строится не по одному контракту, а по нескольким NG-инструментам.
# Скрипт не меняет БД, runtime_active_universe и execution.


TRADES_SQL = """
WITH base AS (
    SELECT
        id,
        symbol,
        side,
        qty::numeric AS qty,
        price::numeric AS price,
        COALESCE(commission, 0)::numeric AS commission,
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
    resolved_strategy AS strategy,
    resolved_timeframe AS timeframe,
    resolved_continuous_symbol AS continuous_symbol,
    signal_reason,
    created_at,
    payload
FROM base
WHERE (
       upper(symbol) LIKE 'NG%%'
    OR upper(resolved_continuous_symbol) LIKE 'NG%%'
    OR upper(resolved_strategy) LIKE 'NG%%'
)
ORDER BY resolved_strategy, resolved_timeframe, resolved_continuous_symbol, symbol, created_at, id
LIMIT %s;
"""


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def lower(value: Any) -> str:
    return text(value).lower()


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def side_sign(side: str) -> int:
    value = text(side).upper()
    if value == "BUY":
        return 1
    if value == "SELL":
        return -1
    return 0


def trade_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        text(row.get("strategy")) or "UNKNOWN",
        text(row.get("timeframe")) or "UNKNOWN",
        text(row.get("continuous_symbol")) or text(row.get("symbol")) or "UNKNOWN",
        text(row.get("symbol")) or "UNKNOWN",
    )


def session_msk(ts: Any) -> str:
    hour_utc = int(ts.hour)
    hour_msk = (hour_utc + 3) % 24

    if 7 <= hour_msk < 10:
        return "утро_мск"
    if 10 <= hour_msk < 14:
        return "московская_середина"
    if 14 <= hour_msk < 19:
        return "вечерняя_сессия"
    if 19 <= hour_msk < 24:
        return "поздняя_сессия"
    return "ночь_или_азиатская"


def classify_signal(row: dict[str, Any]) -> str:
    haystack_parts: list[str] = [
        lower(row.get("signal_reason")),
        lower(row.get("strategy")),
        lower(row.get("timeframe")),
        lower(row.get("symbol")),
    ]

    payload = row.get("payload") or {}
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
        ):
            if payload.get(key) is not None:
                haystack_parts.append(str(payload.get(key)).lower())

        for nested_key in ("metadata", "trade_context_snapshot", "features"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict):
                for key, value in nested.items():
                    haystack_parts.append(str(key).lower())
                    if value is not None:
                        haystack_parts.append(str(value).lower())

    haystack = " ".join(haystack_parts)

    if "smart_entry_retest" in haystack or "retest" in haystack:
        return "SMART_ENTRY_RETEST"
    if "time_exit" in haystack or "timeout" in haystack:
        return "TIME_EXIT"
    if "breakout" in haystack or "break_out" in haystack:
        return "BREAKOUT"
    if "regime" in haystack:
        return "REGIME_FILTER"

    return "OTHER"


def bucket_add(bucket: dict[tuple[str, ...], dict[str, Any]], key: tuple[str, ...], pair: dict[str, Any]) -> None:
    item = bucket.setdefault(
        key,
        {
            "pairs": 0,
            "wins": 0,
            "losses": 0,
            "flat": 0,
            "gross_pnl": 0.0,
            "commission": 0.0,
            "net_pnl": 0.0,
            "symbols": set(),
            "first_entry": None,
            "last_exit": None,
        },
    )

    item["pairs"] += 1
    item["gross_pnl"] += pair["gross_pnl"]
    item["commission"] += pair["commission"]
    item["net_pnl"] += pair["net_pnl"]
    item["symbols"].add(pair["symbol"])

    if pair["net_pnl"] > 0:
        item["wins"] += 1
    elif pair["net_pnl"] < 0:
        item["losses"] += 1
    else:
        item["flat"] += 1

    if item["first_entry"] is None or pair["entry_ts"] < item["first_entry"]:
        item["first_entry"] = pair["entry_ts"]
    if item["last_exit"] is None or pair["exit_ts"] > item["last_exit"]:
        item["last_exit"] = pair["exit_ts"]


def print_bucket(title: str, prefix: str, bucket: dict[tuple[str, ...], dict[str, Any]], names: tuple[str, ...]) -> None:
    print()
    print(title)

    for key, item in sorted(bucket.items(), key=lambda kv: (kv[0], kv[1]["net_pnl"])):
        pairs = item["pairs"]
        winrate = item["wins"] / pairs if pairs else 0.0
        net_per_pair = item["net_pnl"] / pairs if pairs else 0.0
        symbols_count = len(item["symbols"])

        key_part = " ".join(f"{name}={value}" for name, value in zip(names, key))

        print(
            f"{prefix} "
            f"{key_part} "
            f"pairs={pairs} "
            f"symbols_count={symbols_count} "
            f"symbols={','.join(sorted(item['symbols']))} "
            f"wins={item['wins']} "
            f"losses={item['losses']} "
            f"flat={item['flat']} "
            f"winrate={winrate:.4f} "
            f"gross_pnl={item['gross_pnl']:.6f} "
            f"commission={item['commission']:.6f} "
            f"net_pnl={item['net_pnl']:.6f} "
            f"net_pnl_per_pair={net_per_pair:.6f} "
            f"first_entry={item['first_entry']} "
            f"last_exit={item['last_exit']}"
        )


def build_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}

    for row in rows:
        rows_by_key.setdefault(trade_key(row), []).append(row)

    pairs: list[dict[str, Any]] = []

    for key, group_rows in rows_by_key.items():
        open_lots: list[dict[str, Any]] = []

        for row in group_rows:
            qty = abs(to_float(row.get("qty")))
            sign = side_sign(text(row.get("side")))

            if qty <= 0 or sign == 0:
                continue

            remaining = qty

            while remaining > 1e-12 and open_lots and open_lots[0]["sign"] != sign:
                lot = open_lots[0]
                entry = lot["row"]
                exit_row = row

                matched_qty = min(remaining, lot["remaining_qty"])

                entry_sign = lot["sign"]
                entry_price = to_float(entry.get("price"))
                exit_price = to_float(exit_row.get("price"))

                gross_pnl = (exit_price - entry_price) * matched_qty * entry_sign

                entry_commission = to_float(entry.get("commission")) * (
                    matched_qty / max(abs(to_float(entry.get("qty"))), 1e-12)
                )
                exit_commission = to_float(exit_row.get("commission")) * (
                    matched_qty / max(abs(to_float(exit_row.get("qty"))), 1e-12)
                )

                commission = entry_commission + exit_commission
                net_pnl = gross_pnl - commission

                entry_signal_class = classify_signal(entry)
                exit_signal_class = classify_signal(exit_row)

                if entry_signal_class == "SMART_ENTRY_RETEST":
                    strategy, timeframe, continuous_symbol, symbol = key
                    pairs.append(
                        {
                            "strategy": strategy,
                            "timeframe": timeframe,
                            "continuous_symbol": continuous_symbol,
                            "symbol": symbol,
                            "entry_signal_class": entry_signal_class,
                            "exit_signal_class": exit_signal_class,
                            "entry_session": session_msk(entry.get("created_at")),
                            "exit_session": session_msk(exit_row.get("created_at")),
                            "entry_side": text(entry.get("side")).upper(),
                            "exit_side": text(exit_row.get("side")).upper(),
                            "qty": matched_qty,
                            "gross_pnl": gross_pnl,
                            "commission": commission,
                            "net_pnl": net_pnl,
                            "entry_ts": entry.get("created_at"),
                            "exit_ts": exit_row.get("created_at"),
                        }
                    )

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

    return pairs


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    lookback = os.getenv("NG_SESSION_FILTER_LOOKBACK", "60 days")
    limit = int(os.getenv("NG_SESSION_FILTER_LIMIT", "100000"))

    print("=== NG SESSION FILTER HYPOTHESIS V1 ===")
    print("mode=read_only")
    print("scope=multi_ng_contracts")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback={lookback}")
    print(f"limit={limit}")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(TRADES_SQL, (lookback, limit))
            rows = [dict(r) for r in cur.fetchall()]

    pairs = build_pairs(rows)

    by_session: dict[tuple[str, str, str], dict[str, Any]] = {}
    by_symbol_session: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_exit_session: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for pair in pairs:
        bucket_add(
            by_session,
            (
                pair["strategy"],
                pair["timeframe"],
                pair["entry_session"],
            ),
            pair,
        )

        bucket_add(
            by_symbol_session,
            (
                pair["strategy"],
                pair["timeframe"],
                pair["symbol"],
                pair["entry_session"],
            ),
            pair,
        )

        bucket_add(
            by_exit_session,
            (
                pair["strategy"],
                pair["timeframe"],
                pair["entry_session"],
                pair["exit_signal_class"],
            ),
            pair,
        )

    print_bucket(
        "NG_SESSION_FILTER_BY_SESSION",
        "NG_SESSION_FILTER_SESSION_ROW",
        by_session,
        ("strategy", "timeframe", "entry_session"),
    )

    print_bucket(
        "NG_SESSION_FILTER_BY_SYMBOL_SESSION",
        "NG_SESSION_FILTER_SYMBOL_SESSION_ROW",
        by_symbol_session,
        ("strategy", "timeframe", "symbol", "entry_session"),
    )

    print_bucket(
        "NG_SESSION_FILTER_BY_EXIT_SESSION",
        "NG_SESSION_FILTER_EXIT_SESSION_ROW",
        by_exit_session,
        ("strategy", "timeframe", "entry_session", "exit_signal_class"),
    )

    total_pairs = len(pairs)
    total_wins = sum(1 for p in pairs if p["net_pnl"] > 0)
    total_losses = sum(1 for p in pairs if p["net_pnl"] < 0)
    total_net_pnl = sum(float(p["net_pnl"]) for p in pairs)
    total_gross_pnl = sum(float(p["gross_pnl"]) for p in pairs)
    total_commission = sum(float(p["commission"]) for p in pairs)
    symbols = sorted({p["symbol"] for p in pairs})
    sessions = sorted({p["entry_session"] for p in pairs})

    positive_sessions = 0
    confirmed_sessions = 0

    for key, item in by_session.items():
        pairs_count = item["pairs"]
        net_per_pair = item["net_pnl"] / pairs_count if pairs_count else 0.0
        if item["net_pnl"] > 0:
            positive_sessions += 1
        if pairs_count >= 30 and item["net_pnl"] > 0 and net_per_pair >= 0.01:
            confirmed_sessions += 1

    print()
    print("NG_SESSION_FILTER_HYPOTHESIS_SUMMARY")
    print(f"rows_loaded={len(rows)}")
    print(f"pairs_total={total_pairs}")
    print(f"symbols_count={len(symbols)}")
    print(f"symbols={','.join(symbols)}")
    print(f"sessions_count={len(sessions)}")
    print(f"sessions={','.join(sessions)}")
    print(f"wins={total_wins}")
    print(f"losses={total_losses}")
    print(f"winrate={(total_wins / total_pairs if total_pairs else 0.0):.4f}")
    print(f"total_gross_pnl={total_gross_pnl:.6f}")
    print(f"total_commission={total_commission:.6f}")
    print(f"total_net_pnl={total_net_pnl:.6f}")
    print(f"net_pnl_per_pair={(total_net_pnl / total_pairs if total_pairs else 0.0):.6f}")
    print(f"positive_sessions={positive_sessions}")
    print(f"confirmed_sessions={confirmed_sessions}")
    print("db_update=0")

    if total_pairs == 0:
        print("VERDICT=NG_SESSION_FILTER_NO_PAIRS")
    elif confirmed_sessions > 0:
        print("VERDICT=NG_SESSION_FILTER_HAS_CONFIRMED_SESSION_CANDIDATE")
    elif positive_sessions > 0:
        print("VERDICT=NG_SESSION_FILTER_HAS_WEAK_SESSION_HYPOTHESIS")
    else:
        print("VERDICT=NG_SESSION_FILTER_NO_CONFIRMED_EDGE")

    print("NG_SESSION_FILTER_HYPOTHESIS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
