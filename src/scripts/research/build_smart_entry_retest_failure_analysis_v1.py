#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


# Русский комментарий:
# SMART_ENTRY_RETEST_FAILURE_ANALYSIS_V1 — read-only анализ провала smart_entry_retest.
# Ничего не пишет в БД, не меняет runtime, не включает execution.
# Строит FIFO-пары сделок и анализирует только пары, где вход был SMART_ENTRY_RETEST.


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


def session_msk(ts: Any) -> str:
    # Русский комментарий:
    # created_at приходит timezone-aware. PostgreSQL в UTC, MSK = UTC+3.
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


def payload_value(row: dict[str, Any], key: str) -> str:
    payload = row.get("payload") or {}
    if not isinstance(payload, dict):
        return ""

    value = payload.get(key)
    if value is not None:
        return str(value)

    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and metadata.get(key) is not None:
        return str(metadata.get(key))

    snapshot = payload.get("trade_context_snapshot")
    if isinstance(snapshot, dict) and snapshot.get(key) is not None:
        return str(snapshot.get(key))

    features = payload.get("features")
    if isinstance(features, dict) and features.get(key) is not None:
        return str(features.get(key))

    return ""


def bucket_add(bucket: dict[tuple[str, ...], dict[str, Any]], key: tuple[str, ...], pair: dict[str, Any]) -> None:
    item = bucket.setdefault(
        key,
        {
            "pairs": 0,
            "wins": 0,
            "losses": 0,
            "flat": 0,
            "closed_qty": 0.0,
            "gross_pnl": 0.0,
            "commission": 0.0,
            "net_pnl": 0.0,
            "first_entry": None,
            "last_exit": None,
        },
    )

    item["pairs"] += 1
    item["closed_qty"] += pair["qty"]
    item["gross_pnl"] += pair["gross_pnl"]
    item["commission"] += pair["commission"]
    item["net_pnl"] += pair["net_pnl"]

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


def print_bucket(title: str, prefix: str, bucket: dict[tuple[str, ...], dict[str, Any]], key_names: tuple[str, ...]) -> None:
    print()
    print(title)

    sorted_items = sorted(
        bucket.items(),
        key=lambda kv: (kv[1]["net_pnl"], -kv[1]["pairs"]),
    )

    for key, item in sorted_items:
        pairs = int(item["pairs"])
        net_per_pair = item["net_pnl"] / pairs if pairs else 0.0
        winrate = item["wins"] / pairs if pairs else 0.0

        key_part = " ".join(f"{name}={value}" for name, value in zip(key_names, key))

        print(
            f"{prefix} "
            f"{key_part} "
            f"pairs={pairs} "
            f"wins={item['wins']} "
            f"losses={item['losses']} "
            f"flat={item['flat']} "
            f"winrate={winrate:.4f} "
            f"closed_qty={item['closed_qty']:.4f} "
            f"gross_pnl={item['gross_pnl']:.6f} "
            f"commission={item['commission']:.6f} "
            f"net_pnl={item['net_pnl']:.6f} "
            f"net_pnl_per_pair={net_per_pair:.6f} "
            f"first_entry={item['first_entry']} "
            f"last_exit={item['last_exit']}"
        )


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    lookback = os.getenv("SMART_ENTRY_RETEST_LOOKBACK", "30 days")
    limit = int(os.getenv("SMART_ENTRY_RETEST_LIMIT", "50000"))

    print("=== SMART ENTRY RETEST FAILURE ANALYSIS V1 ===")
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

    smart_pairs: list[dict[str, Any]] = []
    open_tail_groups = 0
    open_tail_qty = 0.0

    for key, group_rows in rows_by_key.items():
        open_lots: list[dict[str, Any]] = []

        for row in group_rows:
            qty = abs(_float(row.get("qty")))
            sign = side_sign(_text(row.get("side")))
            if sign == 0 or qty <= 0:
                continue

            remaining = qty

            while remaining > 1e-12 and open_lots and open_lots[0]["sign"] != sign:
                lot = open_lots[0]
                entry = lot["row"]
                exit_row = row

                matched_qty = min(remaining, lot["remaining_qty"])

                entry_sign = lot["sign"]
                entry_price = _float(entry.get("price"))
                exit_price = _float(exit_row.get("price"))

                gross_pnl = (exit_price - entry_price) * matched_qty * entry_sign

                entry_commission = _float(entry.get("commission")) * (
                    matched_qty / max(_float(entry.get("qty")), 1e-12)
                )
                exit_commission = _float(exit_row.get("commission")) * (
                    matched_qty / max(_float(exit_row.get("qty")), 1e-12)
                )
                commission = entry_commission + exit_commission
                net_pnl = gross_pnl - commission

                entry_signal_class = classify_signal(entry)
                exit_signal_class = classify_signal(exit_row)

                if entry_signal_class == "SMART_ENTRY_RETEST":
                    strategy, timeframe, continuous_symbol, symbol = key
                    pair = {
                        "strategy": strategy,
                        "timeframe": timeframe,
                        "continuous_symbol": continuous_symbol,
                        "symbol": symbol,
                        "family": signal_family(symbol, continuous_symbol),
                        "entry_signal_class": entry_signal_class,
                        "exit_signal_class": exit_signal_class,
                        "entry_reason": _text(entry.get("signal_reason")) or "NONE",
                        "exit_reason": _text(exit_row.get("signal_reason")) or "NONE",
                        "entry_side": _text(entry.get("side")).upper(),
                        "exit_side": _text(exit_row.get("side")).upper(),
                        "qty": matched_qty,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "gross_pnl": gross_pnl,
                        "commission": commission,
                        "net_pnl": net_pnl,
                        "entry_ts": entry.get("created_at"),
                        "exit_ts": exit_row.get("created_at"),
                        "entry_session": session_msk(entry.get("created_at")),
                        "exit_session": session_msk(exit_row.get("created_at")),
                        "entry_regime": payload_value(entry, "regime") or "UNKNOWN",
                        "exit_regime": payload_value(exit_row, "regime") or "UNKNOWN",
                        "entry_adaptive_regime_action": payload_value(entry, "adaptive_regime_action") or "UNKNOWN",
                        "entry_quality": payload_value(entry, "quality") or payload_value(entry, "signal_quality") or "UNKNOWN",
                    }
                    smart_pairs.append(pair)

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

        group_open_qty = sum(float(lot["remaining_qty"]) for lot in open_lots)
        if group_open_qty > 1e-12:
            open_tail_groups += 1
            open_tail_qty += group_open_qty

    by_strategy: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_exit: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    by_session: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    by_regime: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}

    for pair in smart_pairs:
        bucket_add(
            by_strategy,
            (
                pair["family"],
                pair["strategy"],
                pair["timeframe"],
                pair["continuous_symbol"],
            ),
            pair,
        )
        bucket_add(
            by_exit,
            (
                pair["family"],
                pair["strategy"],
                pair["timeframe"],
                pair["continuous_symbol"],
                pair["exit_signal_class"],
            ),
            pair,
        )
        bucket_add(
            by_session,
            (
                pair["family"],
                pair["strategy"],
                pair["timeframe"],
                pair["continuous_symbol"],
                pair["entry_session"],
            ),
            pair,
        )
        bucket_add(
            by_regime,
            (
                pair["family"],
                pair["strategy"],
                pair["timeframe"],
                pair["continuous_symbol"],
                pair["entry_regime"],
            ),
            pair,
        )

    print_bucket(
        "SMART_ENTRY_RETEST_BY_STRATEGY",
        "SMART_ENTRY_RETEST_STRATEGY_ROW",
        by_strategy,
        ("family", "strategy", "timeframe", "continuous_symbol"),
    )

    print_bucket(
        "SMART_ENTRY_RETEST_BY_EXIT_CLASS",
        "SMART_ENTRY_RETEST_EXIT_ROW",
        by_exit,
        ("family", "strategy", "timeframe", "continuous_symbol", "exit_signal_class"),
    )

    print_bucket(
        "SMART_ENTRY_RETEST_BY_ENTRY_SESSION",
        "SMART_ENTRY_RETEST_SESSION_ROW",
        by_session,
        ("family", "strategy", "timeframe", "continuous_symbol", "entry_session"),
    )

    print_bucket(
        "SMART_ENTRY_RETEST_BY_ENTRY_REGIME",
        "SMART_ENTRY_RETEST_REGIME_ROW",
        by_regime,
        ("family", "strategy", "timeframe", "continuous_symbol", "entry_regime"),
    )

    pairs_total = len(smart_pairs)
    wins = sum(1 for p in smart_pairs if p["net_pnl"] > 0)
    losses = sum(1 for p in smart_pairs if p["net_pnl"] < 0)
    total_gross_pnl = sum(float(p["gross_pnl"]) for p in smart_pairs)
    total_commission = sum(float(p["commission"]) for p in smart_pairs)
    total_net_pnl = sum(float(p["net_pnl"]) for p in smart_pairs)
    net_pnl_per_pair = total_net_pnl / pairs_total if pairs_total else 0.0
    winrate = wins / pairs_total if pairs_total else 0.0

    print()
    print("SMART_ENTRY_RETEST_FAILURE_ANALYSIS_SUMMARY")
    print(f"pairs_total={pairs_total}")
    print(f"wins={wins}")
    print(f"losses={losses}")
    print(f"winrate={winrate:.4f}")
    print(f"total_gross_pnl={total_gross_pnl:.6f}")
    print(f"total_commission={total_commission:.6f}")
    print(f"total_net_pnl={total_net_pnl:.6f}")
    print(f"net_pnl_per_pair={net_pnl_per_pair:.6f}")
    print(f"open_tail_groups={open_tail_groups}")
    print(f"open_tail_qty={open_tail_qty:.4f}")

    if pairs_total == 0:
        print("VERDICT=SMART_ENTRY_RETEST_NO_PAIRS")
    elif total_net_pnl < 0:
        print("VERDICT=SMART_ENTRY_RETEST_FAILURE_CONFIRMED")
    elif net_pnl_per_pair < 0.01:
        print("VERDICT=SMART_ENTRY_RETEST_EDGE_TOO_WEAK")
    else:
        print("VERDICT=SMART_ENTRY_RETEST_NEEDS_DEEPER_REVIEW")

    print("SMART_ENTRY_RETEST_FAILURE_ANALYSIS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
