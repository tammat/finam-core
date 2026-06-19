#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# DIRTY_TRADE_ORIGIN_AUDIT_V1
# Read-only аудит происхождения "кривых" записей trades.
# Ищет строки с UNKNOWN_SOURCE, UNKNOWN_REASON, commission=0, пустыми strategy/timeframe.
# Цель — понять источник записи: script/source/pipeline/payload/trade_context_snapshot.


LOOKBACK_DAYS = int(os.getenv("DIRTY_TRADE_ORIGIN_LOOKBACK_DAYS", "30"))
SAMPLE_LIMIT = int(os.getenv("DIRTY_TRADE_ORIGIN_SAMPLE_LIMIT", "80"))

SQL = """
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
    payload
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
order by id asc;
"""


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def fnum(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def payload_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def extract_dirty_reason(row: dict[str, Any]) -> list[str]:
    payload = payload_dict(row.get("payload"))

    signal_class = sval(payload.get("signal_class"), "")
    entry_source = sval(payload.get("entry_source_normalized") or payload.get("entry_source") or payload.get("source"), "")
    reason = sval(
        payload.get("entry_reason_normalized")
        or payload.get("reason")
        or payload.get("entry_reason")
        or nested(payload, "features", "reason")
        or nested(payload, "features", "entry_reason"),
        "",
    )

    reasons: list[str] = []

    if not sval(row.get("strategy"), ""):
        reasons.append("missing_strategy")

    if not sval(row.get("timeframe"), ""):
        reasons.append("missing_timeframe")

    if not sval(row.get("continuous_symbol"), ""):
        reasons.append("missing_continuous_symbol")

    if entry_source in {"", "UNKNOWN_SOURCE", "UNKNOWN"}:
        reasons.append("unknown_source")

    if reason in {"", "UNKNOWN_REASON", "UNKNOWN"} and signal_class in {"", "UNKNOWN_REASON", "UNKNOWN"}:
        reasons.append("unknown_reason")

    if fnum(row.get("commission")) == 0.0:
        reasons.append("zero_commission")

    return reasons


def origin_signature(row: dict[str, Any]) -> dict[str, str]:
    payload = payload_dict(row.get("payload"))

    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
    trade_context = payload.get("trade_context_snapshot") if isinstance(payload.get("trade_context_snapshot"), dict) else {}
    edge_gate = trade_context.get("edge_gate") if isinstance(trade_context.get("edge_gate"), dict) else {}

    return {
        "payload_source": sval(payload.get("source"), "NULL"),
        "payload_entry_source": sval(payload.get("entry_source"), "NULL"),
        "entry_source_normalized": sval(payload.get("entry_source_normalized"), "NULL"),
        "payload_reason": sval(payload.get("reason"), "NULL"),
        "payload_entry_reason": sval(payload.get("entry_reason"), "NULL"),
        "entry_reason_normalized": sval(payload.get("entry_reason_normalized"), "NULL"),
        "signal_class": sval(payload.get("signal_class"), "NULL"),
        "features_source": sval(features.get("source"), "NULL"),
        "features_reason": sval(features.get("reason") or features.get("entry_reason"), "NULL"),
        "features_regime": sval(features.get("regime") or features.get("regime_label"), "NULL"),
        "trade_context_strategy": sval(trade_context.get("strategy"), "NULL"),
        "trade_context_timeframe": sval(trade_context.get("timeframe"), "NULL"),
        "trade_context_continuous_symbol": sval(trade_context.get("continuous_symbol"), "NULL"),
        "edge_gate_reason": sval(edge_gate.get("reason"), "NULL"),
        "payload_keys": ",".join(sorted(payload.keys())) if payload else "NO_PAYLOAD",
    }


def compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== DIRTY TRADE ORIGIN AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print(f"sample_limit={SAMPLE_LIMIT}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (interval,))
            rows = list(cur.fetchall())

    total_rows = len(rows)
    dirty_rows = []
    dirty_reason_counter: Counter[str] = Counter()
    origin_counter: Counter[tuple[str, str, str, str, str, str]] = Counter()
    strategy_symbol_counter: Counter[tuple[str, str, str]] = Counter()
    payload_key_counter: Counter[str] = Counter()

    for row in rows:
        reasons = extract_dirty_reason(row)

        if not reasons:
            continue

        dirty_rows.append(row)

        for reason in reasons:
            dirty_reason_counter[reason] += 1

        sig = origin_signature(row)
        origin_key = (
            sig["payload_source"],
            sig["payload_entry_source"],
            sig["entry_source_normalized"],
            sig["payload_reason"],
            sig["entry_reason_normalized"],
            sig["payload_keys"],
        )
        origin_counter[origin_key] += 1

        strategy_symbol_counter[
            (
                sval(row.get("strategy"), "EMPTY_STRATEGY"),
                sval(row.get("timeframe"), "EMPTY_TIMEFRAME"),
                sval(row.get("symbol"), "UNKNOWN_SYMBOL"),
            )
        ] += 1

        payload_key_counter[sig["payload_keys"]] += 1

    print("DIRTY_TRADE_ORIGIN_REASON_ROWS")
    for reason, count in dirty_reason_counter.most_common():
        print(f"DIRTY_TRADE_ORIGIN_REASON_ROW reason={reason} rows={count}")

    print()
    print("DIRTY_TRADE_ORIGIN_GROUP_ROWS")
    for key, count in origin_counter.most_common(50):
        (
            payload_source,
            payload_entry_source,
            entry_source_normalized,
            payload_reason,
            entry_reason_normalized,
            payload_keys,
        ) = key
        print(
            "DIRTY_TRADE_ORIGIN_GROUP_ROW "
            f"rows={count} "
            f"payload_source={payload_source} "
            f"payload_entry_source={payload_entry_source} "
            f"entry_source_normalized={entry_source_normalized} "
            f"payload_reason={payload_reason} "
            f"entry_reason_normalized={entry_reason_normalized} "
            f"payload_keys={payload_keys}"
        )

    print()
    print("DIRTY_TRADE_ORIGIN_STRATEGY_SYMBOL_ROWS")
    for key, count in strategy_symbol_counter.most_common(60):
        strategy, timeframe, symbol = key
        print(
            "DIRTY_TRADE_ORIGIN_STRATEGY_SYMBOL_ROW "
            f"rows={count} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"symbol={symbol}"
        )

    print()
    print("DIRTY_TRADE_ORIGIN_PAYLOAD_KEY_ROWS")
    for payload_keys, count in payload_key_counter.most_common(30):
        print(
            "DIRTY_TRADE_ORIGIN_PAYLOAD_KEY_ROW "
            f"rows={count} "
            f"payload_keys={payload_keys}"
        )

    print()
    print("DIRTY_TRADE_ORIGIN_SAMPLE_ROWS")

    printed = 0
    for row in dirty_rows:
        if printed >= SAMPLE_LIMIT:
            break
        printed += 1

        reasons = extract_dirty_reason(row)
        sig = origin_signature(row)

        print(
            "DIRTY_TRADE_ORIGIN_SAMPLE_ROW "
            f"id={row.get('id')} "
            f"created_at={row.get('created_at')} "
            f"symbol={sval(row.get('symbol'))} "
            f"strategy={sval(row.get('strategy'), 'EMPTY_STRATEGY')} "
            f"timeframe={sval(row.get('timeframe'), 'EMPTY_TIMEFRAME')} "
            f"continuous_symbol={sval(row.get('continuous_symbol'), 'EMPTY_CONT')} "
            f"side={sval(row.get('side'))} "
            f"qty={row.get('qty')} "
            f"price={row.get('price')} "
            f"commission={row.get('commission')} "
            f"dirty_reasons={','.join(reasons)} "
            f"origin={compact_json(sig)}"
        )

    unknown_source_rows = dirty_reason_counter["unknown_source"]
    unknown_reason_rows = dirty_reason_counter["unknown_reason"]
    zero_commission_rows = dirty_reason_counter["zero_commission"]
    missing_strategy_rows = dirty_reason_counter["missing_strategy"]
    missing_timeframe_rows = dirty_reason_counter["missing_timeframe"]

    print()
    print("DIRTY_TRADE_ORIGIN_AUDIT_SUMMARY")
    print(f"rows_total={total_rows}")
    print(f"dirty_rows={len(dirty_rows)}")
    print(f"unknown_source_rows={unknown_source_rows}")
    print(f"unknown_reason_rows={unknown_reason_rows}")
    print(f"zero_commission_rows={zero_commission_rows}")
    print(f"missing_strategy_rows={missing_strategy_rows}")
    print(f"missing_timeframe_rows={missing_timeframe_rows}")
    print(f"origin_groups={len(origin_counter)}")
    print(f"strategy_symbol_groups={len(strategy_symbol_counter)}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")

    if missing_strategy_rows or missing_timeframe_rows:
        print("VERDICT=DIRTY_TRADE_ORIGIN_HAS_CONTEXT_GAPS")
    elif unknown_source_rows or unknown_reason_rows or zero_commission_rows:
        print("VERDICT=DIRTY_TRADE_ORIGIN_IDENTIFIED")
    else:
        print("VERDICT=DIRTY_TRADE_ORIGIN_NO_DIRTY_ROWS")

    print("DIRTY_TRADE_ORIGIN_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
