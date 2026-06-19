#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import Counter
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# DIRTY_TRADE_ORIGIN_PATCH_PLAN_V1
# Read-only план классификации происхождения записей trades.
# Ничего не обновляет. Цель — определить, какие строки можно использовать
# для clean edge, а какие надо исключить/пометить.


LOOKBACK_DAYS = int(os.getenv("DIRTY_TRADE_ORIGIN_LOOKBACK_DAYS", "30"))

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

    print("=== DIRTY TRADE ORIGIN PATCH PLAN V1 ===")
    print("mode=read_only")
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

    class_counter: Counter[str] = Counter()
    reason_counter: Counter[str] = Counter()
    strategy_counter: Counter[tuple[str, str, str, str]] = Counter()

    samples: list[tuple[dict[str, Any], str, str]] = []

    for row in rows:
        cls, reason = classify(row)

        class_counter[cls] += 1
        reason_counter[reason] += 1

        strategy_counter[
            (
                cls,
                sval(row.get("strategy"), "EMPTY_STRATEGY"),
                sval(row.get("timeframe"), "EMPTY_TIMEFRAME"),
                sval(row.get("symbol"), "UNKNOWN_SYMBOL"),
            )
        ] += 1

        if len(samples) < 80:
            samples.append((row, cls, reason))

    print("DIRTY_TRADE_ORIGIN_PATCH_CLASS_ROWS")
    for cls, count in class_counter.most_common():
        print(f"DIRTY_TRADE_ORIGIN_PATCH_CLASS_ROW class={cls} rows={count}")

    print()
    print("DIRTY_TRADE_ORIGIN_PATCH_REASON_ROWS")
    for reason, count in reason_counter.most_common():
        print(f"DIRTY_TRADE_ORIGIN_PATCH_REASON_ROW reason={reason} rows={count}")

    print()
    print("DIRTY_TRADE_ORIGIN_PATCH_STRATEGY_ROWS")
    for key, count in strategy_counter.most_common(80):
        cls, strategy, timeframe, symbol = key
        print(
            "DIRTY_TRADE_ORIGIN_PATCH_STRATEGY_ROW "
            f"class={cls} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"symbol={symbol} "
            f"rows={count}"
        )

    print()
    print("DIRTY_TRADE_ORIGIN_PATCH_SAMPLE_ROWS")
    for row, cls, reason in samples:
        print(
            "DIRTY_TRADE_ORIGIN_PATCH_SAMPLE_ROW "
            f"id={row.get('id')} "
            f"created_at={row.get('created_at')} "
            f"symbol={sval(row.get('symbol'))} "
            f"strategy={sval(row.get('strategy'), 'EMPTY_STRATEGY')} "
            f"timeframe={sval(row.get('timeframe'), 'EMPTY_TIMEFRAME')} "
            f"continuous_symbol={sval(row.get('continuous_symbol'), 'EMPTY_CONT')} "
            f"commission={row.get('commission')} "
            f"class={cls} "
            f"reason={reason}"
        )

    clean_rows = class_counter["RUNTIME_OR_PAPER_CLEAN_ENOUGH"]
    historical_rows = class_counter["HISTORICAL_REPLAY"]
    legacy_ng_rows = class_counter["LEGACY_NG_SYNTHETIC_BACKFILL"]
    context_gap_rows = class_counter["CONTEXT_GAP_REVIEW"]
    no_payload_rows = class_counter["NO_PAYLOAD_REVIEW"]

    print()
    print("DIRTY_TRADE_ORIGIN_PATCH_PLAN_SUMMARY")
    print(f"rows_total={len(rows)}")
    print(f"clean_runtime_or_paper_rows={clean_rows}")
    print(f"historical_replay_rows={historical_rows}")
    print(f"legacy_ng_synthetic_backfill_rows={legacy_ng_rows}")
    print(f"context_gap_review_rows={context_gap_rows}")
    print(f"no_payload_review_rows={no_payload_rows}")
    print(f"classes_total={len(class_counter)}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("recommended_add_trade_source_classification=1")
    print("recommended_exclude_legacy_ng_from_clean_edge=1")
    print("recommended_keep_historical_replay_separate=1")
    print("recommended_fix_paper_fill_fallback_writer=1")

    if legacy_ng_rows > 0 or context_gap_rows > 0 or no_payload_rows > 0:
        print("VERDICT=DIRTY_TRADE_ORIGIN_PATCH_PLAN_REQUIRED")
    else:
        print("VERDICT=DIRTY_TRADE_ORIGIN_PATCH_PLAN_NO_ACTION_REQUIRED")

    print("DIRTY_TRADE_ORIGIN_PATCH_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
