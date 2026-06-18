#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_V1
# Применяет нормализацию только для SAFE_UPDATE:
# - payload.signal_class
# - payload.signal_params
# - payload.entry_reason_normalized
# - payload.entry_source_normalized
# - payload.entry_regime_normalized
# Не трогает UNKNOWN_REASON.
# Не перезаписывает существующий payload.signal_class.


LOOKBACK_DAYS = int(os.getenv("SIGNAL_CLASS_NORMALIZATION_LOOKBACK_DAYS", "30"))
APPLY = os.getenv("APPLY", "0") == "1"

NUMERIC_TOKEN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
SPACES_RE = re.compile(r"\s+")

SELECT_SQL = """
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

UPDATE_SQL = """
update trades
set payload = %s::jsonb
where id = %s
  and payload->>'signal_class' is null;
"""


def payload_dict(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def features(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("features") if isinstance(payload.get("features"), dict) else {}


def extract_reason(payload: dict[str, Any]) -> str:
    f = features(payload)
    return str(
        payload.get("reason")
        or payload.get("entry_reason")
        or f.get("reason")
        or f.get("entry_reason")
        or "UNKNOWN_REASON"
    ).strip()


def extract_source(payload: dict[str, Any]) -> str:
    f = features(payload)
    return str(
        payload.get("source")
        or payload.get("entry_source")
        or f.get("source")
        or "UNKNOWN_SOURCE"
    ).strip()


def extract_regime(payload: dict[str, Any]) -> str:
    f = features(payload)
    return str(
        f.get("regime")
        or f.get("regime_label")
        or payload.get("regime")
        or "UNKNOWN_REGIME"
    ).strip()


def normalize_reason(reason: str) -> tuple[str, dict[str, str]]:
    params = dict(NUMERIC_TOKEN_RE.findall(reason or ""))
    normalized = NUMERIC_TOKEN_RE.sub(" ", reason or "")
    normalized = SPACES_RE.sub(" ", normalized).strip()
    return normalized or "UNKNOWN_REASON", params


def build_updated_payload(row: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    payload = payload_dict(row.get("payload")).copy()
    reason = extract_reason(payload)
    source = extract_source(payload)
    regime = extract_regime(payload)
    signal_class, params = normalize_reason(reason)

    review_reasons: list[str] = []

    if payload.get("signal_class"):
        review_reasons.append("signal_class_already_exists")
        return None, review_reasons

    if signal_class == "UNKNOWN_REASON":
        review_reasons.append("unknown_reason")
        return None, review_reasons

    if source == "UNKNOWN_SOURCE":
        review_reasons.append("unknown_source")

    if not str(row.get("strategy") or "").strip():
        review_reasons.append("missing_strategy")

    if not str(row.get("timeframe") or "").strip():
        review_reasons.append("missing_timeframe")

    payload["signal_class"] = signal_class
    payload["signal_params"] = params
    payload["entry_reason_normalized"] = signal_class
    payload["entry_source_normalized"] = source
    payload["entry_regime_normalized"] = regime
    payload["signal_normalization_version"] = "v1"

    if review_reasons:
        payload["signal_normalization_review_reasons"] = review_reasons

    return payload, review_reasons


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== SIGNAL CLASS NORMALIZATION BACKFILL APPLY V1 ===")
    print(f"mode={'apply' if APPLY else 'dry_run'}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print(f"db_update={1 if APPLY else 0}")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    safe_updates = 0
    review_only = 0
    unknown_reason_rows = 0
    unknown_source_rows = 0
    missing_strategy_rows = 0
    missing_timeframe_rows = 0
    updated_rows = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SELECT_SQL, (interval,))
            rows = list(cur.fetchall())

            print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_ROWS")

            for row in rows:
                updated_payload, review_reasons = build_updated_payload(row)

                if updated_payload is None:
                    review_only += 1
                    if "unknown_reason" in review_reasons:
                        unknown_reason_rows += 1
                    continue

                safe_updates += 1

                if "unknown_source" in review_reasons:
                    unknown_source_rows += 1
                if "missing_strategy" in review_reasons:
                    missing_strategy_rows += 1
                if "missing_timeframe" in review_reasons:
                    missing_timeframe_rows += 1

                if safe_updates <= 40:
                    print(
                        "SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_ROW "
                        f"id={row.get('id')} "
                        f"symbol={row.get('symbol')} "
                        f"strategy={row.get('strategy')} "
                        f"timeframe={row.get('timeframe')} "
                        f"signal_class={updated_payload.get('signal_class')} "
                        f"param_keys={','.join(sorted((updated_payload.get('signal_params') or {}).keys())) or 'NONE'} "
                        f"review_reasons={','.join(review_reasons) if review_reasons else 'NONE'}"
                    )

                if APPLY:
                    cur.execute(
                        UPDATE_SQL,
                        (
                            json.dumps(updated_payload, ensure_ascii=False),
                            row["id"],
                        ),
                    )
                    updated_rows += int(cur.rowcount or 0)

            if APPLY:
                conn.commit()
            else:
                conn.rollback()

    print()
    print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_SUMMARY")
    print(f"rows_total={len(rows)}")
    print(f"safe_updates={safe_updates}")
    print(f"review_only={review_only}")
    print(f"unknown_reason_rows={unknown_reason_rows}")
    print(f"unknown_source_rows={unknown_source_rows}")
    print(f"missing_strategy_rows={missing_strategy_rows}")
    print(f"missing_timeframe_rows={missing_timeframe_rows}")
    print(f"updated_rows={updated_rows}")
    print(f"db_update={1 if APPLY else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if not APPLY:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_READY")
    elif updated_rows == safe_updates:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_OK")
    elif updated_rows == 0 and safe_updates == 0:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_ALREADY_APPLIED")
    else:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_REVIEW_REQUIRED")

    print("SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
