#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import Counter
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_V1
# Dry-run применения payload.trade_source_class.
# Ничего не обновляет в БД.
# Проверяет, сколько строк будет обновлено и какие значения будут записаны.


LOOKBACK_DAYS = int(os.getenv("TRADE_SOURCE_CLASS_LOOKBACK_DAYS", "30"))
SAMPLE_LIMIT = int(os.getenv("TRADE_SOURCE_CLASS_SAMPLE_LIMIT", "80"))

SQL = """
select
    id,
    created_at,
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

    print("=== TRADE SOURCE CLASSIFICATION BACKFILL APPLY DRY RUN V1 ===")
    print("mode=apply_dry_run")
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
    planned_updates = 0
    already_classified = 0
    no_payload_rows = 0

    class_counter: Counter[str] = Counter()
    reason_counter: Counter[str] = Counter()

    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_ROWS")

    printed = 0
    for row in rows:
        rows_total += 1
        payload = payload_dict(row.get("payload"))

        if not payload:
            no_payload_rows += 1

        if payload.get("trade_source_class"):
            already_classified += 1
            continue

        trade_source_class, reason = classify(row)
        class_counter[trade_source_class] += 1
        reason_counter[reason] += 1
        planned_updates += 1

        if printed < SAMPLE_LIMIT:
            printed += 1
            print(
                "TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_ROW "
                f"id={row.get('id')} "
                f"symbol={sval(row.get('symbol'))} "
                f"strategy={sval(row.get('strategy'), 'EMPTY_STRATEGY')} "
                f"timeframe={sval(row.get('timeframe'), 'EMPTY_TIMEFRAME')} "
                f"continuous_symbol={sval(row.get('continuous_symbol'), 'EMPTY_CONT')} "
                f"commission={row.get('commission')} "
                f"trade_source_class={trade_source_class} "
                f"trade_source_class_reason={reason} "
                f"would_update=1"
            )

    print()
    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_CLASS_ROWS")
    for cls, count in class_counter.most_common():
        print(f"TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_CLASS_ROW class={cls} rows={count}")

    print()
    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_REASON_ROWS")
    for reason, count in reason_counter.most_common():
        print(f"TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_REASON_ROW reason={reason} rows={count}")

    print()
    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_SUMMARY")
    print(f"rows_total={rows_total}")
    print(f"planned_updates={planned_updates}")
    print(f"already_classified={already_classified}")
    print(f"no_payload_rows={no_payload_rows}")
    print(f"class_kinds={len(class_counter)}")
    print(f"clean_runtime_or_paper_rows={class_counter['RUNTIME_OR_PAPER_CLEAN_ENOUGH']}")
    print(f"historical_replay_rows={class_counter['HISTORICAL_REPLAY']}")
    print(f"legacy_ng_synthetic_backfill_rows={class_counter['LEGACY_NG_SYNTHETIC_BACKFILL']}")
    print(f"normalized_but_not_clean_edge_rows={class_counter['NORMALIZED_BUT_NOT_CLEAN_EDGE']}")
    print(f"paper_fill_fallback_rows={class_counter['PAPER_FILL_FALLBACK']}")
    print(f"context_gap_review_rows={class_counter['CONTEXT_GAP_REVIEW']}")
    print(f"no_payload_review_rows={class_counter['NO_PAYLOAD_REVIEW']}")
    print(f"review_required_rows={class_counter['REVIEW_REQUIRED']}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("apply_allowed=0")

    if planned_updates == rows_total and already_classified == 0:
        print("VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_READY")
    elif planned_updates > 0:
        print("VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_PARTIAL_READY")
    else:
        print("VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_NO_CHANGE_REQUIRED")

    print("TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
