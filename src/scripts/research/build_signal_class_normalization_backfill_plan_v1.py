#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_V1
# Dry-run план нормализации signal_class в trades.payload.
# Ничего не обновляет в БД.


LOOKBACK_DAYS = int(os.getenv("SIGNAL_CLASS_NORMALIZATION_LOOKBACK_DAYS", "30"))

NUMERIC_TOKEN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
SPACES_RE = re.compile(r"\s+")

SQL = """
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    payload,
    commission
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
order by created_at asc, id asc;
"""


def fmt(v: Any) -> str:
    if v is None:
        return "NULL"
    return str(v)


def payload_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def extract_reason(payload: dict[str, Any]) -> str:
    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
    return str(
        payload.get("reason")
        or payload.get("entry_reason")
        or features.get("reason")
        or features.get("entry_reason")
        or "UNKNOWN_REASON"
    ).strip()


def extract_source(payload: dict[str, Any]) -> str:
    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
    return str(
        payload.get("source")
        or payload.get("entry_source")
        or features.get("source")
        or "UNKNOWN_SOURCE"
    ).strip()


def extract_regime(payload: dict[str, Any]) -> str:
    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}
    return str(
        features.get("regime")
        or features.get("regime_label")
        or payload.get("regime")
        or "UNKNOWN_REGIME"
    ).strip()


def normalize_reason(reason: str) -> tuple[str, dict[str, str]]:
    params = dict(NUMERIC_TOKEN_RE.findall(reason or ""))
    normalized = NUMERIC_TOKEN_RE.sub(" ", reason or "")
    normalized = SPACES_RE.sub(" ", normalized).strip()
    return normalized or "UNKNOWN_REASON", params


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== SIGNAL CLASS NORMALIZATION BACKFILL PLAN V1 ===")
    print("mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (interval,))
            rows = list(cur.fetchall())

    planned_updates = 0
    missing_strategy = 0
    missing_timeframe = 0
    unknown_source = 0
    unknown_reason = 0
    dynamic_reason = 0
    missing_signal_class = 0

    class_counter: Counter[str] = Counter()
    param_counter: Counter[str] = Counter()

    print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_ROWS")

    for row in rows:
        payload = payload_dict(row.get("payload"))
        reason = extract_reason(payload)
        source = extract_source(payload)
        regime = extract_regime(payload)
        normalized_reason, params = normalize_reason(reason)

        signal_class = normalized_reason
        class_counter[signal_class] += 1
        for key in params:
            param_counter[key] += 1

        has_signal_class = bool(payload.get("signal_class"))
        needs_update = False

        if not has_signal_class:
            missing_signal_class += 1
            needs_update = True

        if params:
            dynamic_reason += 1
            needs_update = True

        if source == "UNKNOWN_SOURCE":
            unknown_source += 1
            needs_update = True

        if reason == "UNKNOWN_REASON" or normalized_reason == "UNKNOWN_REASON":
            unknown_reason += 1

        if not str(row.get("strategy") or "").strip():
            missing_strategy += 1

        if not str(row.get("timeframe") or "").strip():
            missing_timeframe += 1

        if needs_update:
            planned_updates += 1

        if needs_update and planned_updates <= 80:
            print(
                "SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_ROW "
                f"id={row.get('id')} "
                f"symbol={fmt(row.get('symbol'))} "
                f"strategy={fmt(row.get('strategy'))} "
                f"timeframe={fmt(row.get('timeframe'))} "
                f"entry_source={source} "
                f"raw_reason={reason} "
                f"signal_class={signal_class} "
                f"entry_regime={regime} "
                f"param_keys={','.join(sorted(params)) if params else 'NONE'} "
                f"planned_update=1"
            )

    print()
    print("SIGNAL_CLASS_NORMALIZATION_CLASS_TOP")
    for signal_class, count in class_counter.most_common(20):
        print(f"SIGNAL_CLASS_NORMALIZATION_CLASS_ROW signal_class={signal_class} trades={count}")

    print()
    print("SIGNAL_CLASS_NORMALIZATION_PARAM_TOP")
    for param_key, count in param_counter.most_common(20):
        print(f"SIGNAL_CLASS_NORMALIZATION_PARAM_ROW param_key={param_key} rows={count}")

    print()
    print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_SUMMARY")
    print(f"trades_total={len(rows)}")
    print(f"planned_updates={planned_updates}")
    print(f"missing_signal_class={missing_signal_class}")
    print(f"dynamic_reason_rows={dynamic_reason}")
    print(f"unknown_source_rows={unknown_source}")
    print(f"unknown_reason_rows={unknown_reason}")
    print(f"missing_strategy_rows={missing_strategy}")
    print(f"missing_timeframe_rows={missing_timeframe}")
    print(f"normalized_classes={len(class_counter)}")
    print(f"param_keys_total={len(param_counter)}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("recommended_apply_requires_manual_confirmation=1")

    if planned_updates > 0:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_READY")
    else:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_NO_CHANGE_REQUIRED")

    print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
