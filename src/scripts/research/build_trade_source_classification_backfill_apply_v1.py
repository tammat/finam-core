#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_V1
# Применяет payload.trade_source_class к существующим trades.
# Не меняет symbol/strategy/timeframe/price/qty/commission.
# Записывает только JSONB-поля классификации источника сделки.


LOOKBACK_DAYS = int(os.getenv("TRADE_SOURCE_CLASS_LOOKBACK_DAYS", "30"))
APPLY = os.getenv("APPLY_TRADE_SOURCE_CLASSIFICATION", "0") == "1"
VERSION = "trade_source_classification_v1"


SQL = """
select
    id,
    symbol,
    strategy,
    timeframe,
    continuous_symbol,
    commission,
    payload
from trades
where created_at >= now() - (%s::text)::interval
  and coalesce(is_invalid, false) = false
order by id asc;
"""


UPDATE_SQL = """
update trades
set payload = coalesce(payload, '{}'::jsonb)
    || %s::jsonb
where id = %s;
"""


def sval(value: Any, default: str = "") -> str:
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


def classify(row: dict[str, Any]) -> tuple[str, str]:
    payload = payload_dict(row.get("payload"))
    keys = set(payload.keys())

    source = sval(payload.get("source"))
    strategy = sval(row.get("strategy"))
    timeframe = sval(row.get("timeframe"))
    continuous_symbol = sval(row.get("continuous_symbol"))
    commission = fnum(row.get("commission"))

    has_trade_context = isinstance(payload.get("trade_context_snapshot"), dict)
    has_signal_class = bool(payload.get("signal_class"))

    if source == "historical_signal_replay_backfill":
        return "HISTORICAL_REPLAY", "payload_source_historical_signal_replay_backfill"

    if source == "paper_fill_fallback":
        return "PAPER_FILL_FALLBACK", "payload_source_paper_fill_fallback"

    if not payload:
        return "NO_PAYLOAD_REVIEW", "payload_empty"

    legacy_ng_keys = {
        "atr_expansion",
        "atr_percent",
        "breakout_strength",
        "chain_id",
        "compression_score",
        "ema_slope",
        "range_expansion",
        "regime",
        "regime_v2",
        "session_bucket",
    }

    if legacy_ng_keys.issubset(keys) and commission == 0.0 and not continuous_symbol:
        return "LEGACY_NG_SYNTHETIC_BACKFILL", "legacy_ng_feature_payload_zero_commission_no_continuous_symbol"

    if not strategy or not timeframe:
        return "CONTEXT_GAP_REVIEW", "missing_strategy_or_timeframe"

    if has_trade_context and commission > 0:
        return "RUNTIME_OR_PAPER_CLEAN_ENOUGH", "has_trade_context_and_commission"

    if has_signal_class and commission == 0.0:
        return "NORMALIZED_BUT_NOT_CLEAN_EDGE", "has_signal_class_but_zero_commission"

    return "REVIEW_REQUIRED", "unclassified"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== TRADE SOURCE CLASSIFICATION BACKFILL APPLY V1 ===")
    print("mode=apply" if APPLY else "mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print(f"db_update={1 if APPLY else 0}")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print(f"classification_version={VERSION}")
    print()

    class_counter: Counter[str] = Counter()
    already_classified = 0
    planned_updates = 0
    updated_rows = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (interval,))
            rows = list(cur.fetchall())

        with conn.cursor() as cur:
            for row in rows:
                payload = payload_dict(row.get("payload"))

                if payload.get("trade_source_class"):
                    already_classified += 1
                    continue

                trade_source_class, reason = classify(row)
                class_counter[trade_source_class] += 1
                planned_updates += 1

                patch = {
                    "trade_source_class": trade_source_class,
                    "trade_source_class_reason": reason,
                    "trade_source_class_version": VERSION,
                }

                if APPLY:
                    cur.execute(UPDATE_SQL, (json.dumps(patch, ensure_ascii=False), row["id"]))
                    updated_rows += 1

        if APPLY:
            conn.commit()
        else:
            conn.rollback()

    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_CLASS_ROWS")
    for cls, count in class_counter.most_common():
        print(f"TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_CLASS_ROW class={cls} rows={count}")

    print()
    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_SUMMARY")
    print(f"rows_total={len(rows)}")
    print(f"planned_updates={planned_updates}")
    print(f"already_classified={already_classified}")
    print(f"updated_rows={updated_rows}")
    print(f"clean_runtime_or_paper_rows={class_counter['RUNTIME_OR_PAPER_CLEAN_ENOUGH']}")
    print(f"historical_replay_rows={class_counter['HISTORICAL_REPLAY']}")
    print(f"legacy_ng_synthetic_backfill_rows={class_counter['LEGACY_NG_SYNTHETIC_BACKFILL']}")
    print(f"normalized_but_not_clean_edge_rows={class_counter['NORMALIZED_BUT_NOT_CLEAN_EDGE']}")
    print(f"paper_fill_fallback_rows={class_counter['PAPER_FILL_FALLBACK']}")
    print(f"context_gap_review_rows={class_counter['CONTEXT_GAP_REVIEW']}")
    print(f"no_payload_review_rows={class_counter['NO_PAYLOAD_REVIEW']}")
    print(f"review_required_rows={class_counter['REVIEW_REQUIRED']}")
    print(f"db_update={1 if APPLY else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if APPLY and updated_rows == planned_updates and updated_rows > 0:
        print("VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_OK")
    elif not APPLY:
        print("VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_MODE")
    else:
        print("VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_REVIEW_REQUIRED")

    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
