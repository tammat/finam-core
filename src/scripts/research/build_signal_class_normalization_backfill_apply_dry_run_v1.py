#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_V1
# Строит точный JSON dry-run для нормализации trades.payload.
# Никаких UPDATE. db_update=0.


LOOKBACK_DAYS = int(os.getenv("SIGNAL_CLASS_NORMALIZATION_LOOKBACK_DAYS", "30"))
SAMPLE_LIMIT = int(os.getenv("SIGNAL_CLASS_NORMALIZATION_SAMPLE_LIMIT", "50"))

NUMERIC_TOKEN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
SPACES_RE = re.compile(r"\s+")

SQL = """
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    payload
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
order by id asc;
"""


def payload_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def extract_features(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("features") if isinstance(payload.get("features"), dict) else {}


def extract_reason(payload: dict[str, Any]) -> str:
    features = extract_features(payload)
    return str(
        payload.get("reason")
        or payload.get("entry_reason")
        or features.get("reason")
        or features.get("entry_reason")
        or "UNKNOWN_REASON"
    ).strip()


def extract_source(payload: dict[str, Any]) -> str:
    features = extract_features(payload)
    return str(
        payload.get("source")
        or payload.get("entry_source")
        or features.get("source")
        or "UNKNOWN_SOURCE"
    ).strip()


def extract_regime(payload: dict[str, Any]) -> str:
    features = extract_features(payload)
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


def make_patch(row: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload = payload_dict(row.get("payload"))
    reason = extract_reason(payload)
    source = extract_source(payload)
    regime = extract_regime(payload)
    signal_class, params = normalize_reason(reason)

    existing_signal_class = payload.get("signal_class")

    safe_to_update = True
    review_reasons: list[str] = []

    if existing_signal_class:
        safe_to_update = False
        review_reasons.append("signal_class_already_exists")

    if signal_class == "UNKNOWN_REASON":
        safe_to_update = False
        review_reasons.append("unknown_reason")

    if source == "UNKNOWN_SOURCE":
        review_reasons.append("unknown_source")

    if not str(row.get("strategy") or "").strip():
        review_reasons.append("missing_strategy")

    if not str(row.get("timeframe") or "").strip():
        review_reasons.append("missing_timeframe")

    patch = {
        "id": row.get("id"),
        "symbol": row.get("symbol"),
        "strategy": row.get("strategy"),
        "timeframe": row.get("timeframe"),
        "signal_class": signal_class,
        "signal_params": params,
        "entry_source_normalized": source,
        "entry_reason_normalized": signal_class,
        "entry_regime_normalized": regime,
        "safe_to_update": safe_to_update,
        "review_reasons": review_reasons,
    }

    action = "SAFE_UPDATE" if safe_to_update else "REVIEW_ONLY"
    return patch, action


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== SIGNAL CLASS NORMALIZATION BACKFILL APPLY DRY RUN V1 ===")
    print("mode=dry_run")
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

    rows_total = 0
    safe_updates = 0
    review_only = 0
    unknown_reason_rows = 0
    unknown_source_rows = 0
    missing_strategy_rows = 0
    missing_timeframe_rows = 0
    existing_signal_class_rows = 0

    print("SIGNAL_CLASS_NORMALIZATION_APPLY_DRY_RUN_ROWS")

    printed = 0
    for row in rows:
        rows_total += 1
        patch, action = make_patch(row)

        if action == "SAFE_UPDATE":
            safe_updates += 1
        else:
            review_only += 1

        reasons = set(patch["review_reasons"])
        if "unknown_reason" in reasons:
            unknown_reason_rows += 1
        if "unknown_source" in reasons:
            unknown_source_rows += 1
        if "missing_strategy" in reasons:
            missing_strategy_rows += 1
        if "missing_timeframe" in reasons:
            missing_timeframe_rows += 1
        if "signal_class_already_exists" in reasons:
            existing_signal_class_rows += 1

        if printed < SAMPLE_LIMIT:
            printed += 1
            print(
                "SIGNAL_CLASS_NORMALIZATION_APPLY_DRY_RUN_ROW "
                f"action={action} "
                f"id={patch['id']} "
                f"symbol={patch['symbol']} "
                f"strategy={patch['strategy']} "
                f"timeframe={patch['timeframe']} "
                f"signal_class={patch['signal_class']} "
                f"param_keys={','.join(sorted(patch['signal_params'].keys())) if patch['signal_params'] else 'NONE'} "
                f"review_reasons={','.join(patch['review_reasons']) if patch['review_reasons'] else 'NONE'}"
            )
            print(
                "SIGNAL_CLASS_NORMALIZATION_APPLY_DRY_RUN_JSON "
                + json.dumps(patch, ensure_ascii=False, sort_keys=True)
            )

    print()
    print("SIGNAL_CLASS_NORMALIZATION_APPLY_DRY_RUN_SQL_TEMPLATE")
    print("update trades")
    print("set payload = jsonb_set(... signal_class / signal_params / normalized fields ...)")
    print("where id = :id")
    print("  and payload->>'signal_class' is null")
    print("  and signal_class <> 'UNKNOWN_REASON';")

    print()
    print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_SUMMARY")
    print(f"rows_total={rows_total}")
    print(f"safe_updates={safe_updates}")
    print(f"review_only={review_only}")
    print(f"unknown_reason_rows={unknown_reason_rows}")
    print(f"unknown_source_rows={unknown_source_rows}")
    print(f"missing_strategy_rows={missing_strategy_rows}")
    print(f"missing_timeframe_rows={missing_timeframe_rows}")
    print(f"existing_signal_class_rows={existing_signal_class_rows}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("recommended_apply_requires_manual_confirmation=1")

    if safe_updates > 0:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_READY")
    elif review_only > 0:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_REVIEW_ONLY")
    else:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_NO_CHANGE_REQUIRED")

    print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
