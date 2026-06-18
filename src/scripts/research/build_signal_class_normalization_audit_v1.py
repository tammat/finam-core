#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SIGNAL_CLASS_NORMALIZATION_AUDIT_V1
# Read-only аудит: ищет динамические числовые параметры внутри entry_reason.
# Цель — отделить signal_class от параметров, чтобы edge scorecard не дробился на тысячи строк.


LOOKBACK_DAYS = int(os.getenv("SIGNAL_CLASS_NORMALIZATION_LOOKBACK_DAYS", "30"))

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


# Русский комментарий:
# Ищем числовые параметры внутри reason:
# range_high=3.155, atr_ratio=0.001236, x=-0.5, x=.25.
NUMERIC_TOKEN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
SPACES_RE = re.compile(r"\\s+")


def fmt(v: Any) -> str:
    if v is None:
        return "NULL"
    return str(v)


def extract_reason(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "UNKNOWN_REASON"

    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}

    return str(
        payload.get("reason")
        or payload.get("entry_reason")
        or features.get("reason")
        or features.get("entry_reason")
        or "UNKNOWN_REASON"
    ).strip()


def extract_source(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "UNKNOWN_SOURCE"

    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}

    return str(
        payload.get("source")
        or payload.get("entry_source")
        or features.get("source")
        or "UNKNOWN_SOURCE"
    ).strip()


def extract_regime(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "UNKNOWN_REGIME"

    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}

    return str(
        features.get("regime")
        or features.get("regime_label")
        or payload.get("regime")
        or "UNKNOWN_REGIME"
    ).strip()


def normalize_reason(reason: str) -> tuple[str, dict[str, str], int]:
    # Русский комментарий:
    # Отделяем стабильный класс сигнала от динамических числовых параметров.
    # Пример:
    # "ng_breakout_up range_high=3.155 atr_ratio=0.001236"
    # -> normalized_reason="ng_breakout_up"
    # -> params={"range_high": "3.155", "atr_ratio": "0.001236"}
    reason = str(reason or "").strip()
    params = dict(NUMERIC_TOKEN_RE.findall(reason))

    normalized = NUMERIC_TOKEN_RE.sub(" ", reason)
    normalized = SPACES_RE.sub(" ", normalized).strip()

    if not normalized:
        normalized = "UNKNOWN_REASON"

    has_dynamic_params = 1 if params else 0
    return normalized, params, has_dynamic_params


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== SIGNAL CLASS NORMALIZATION AUDIT V1 ===")
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

    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "trades": 0,
            "dynamic_reason_rows": 0,
            "commission": 0.0,
            "example_raw_reason": None,
            "param_keys": set(),
        }
    )

    dynamic_rows = 0
    unknown_source_rows = 0
    unknown_regime_rows = 0

    for row in rows:
        payload = row.get("payload")
        raw_reason = extract_reason(payload)
        source = extract_source(payload)
        regime = extract_regime(payload)
        norm_reason, params, has_dynamic = normalize_reason(raw_reason)

        if has_dynamic:
            dynamic_rows += 1
        if source == "UNKNOWN_SOURCE":
            unknown_source_rows += 1
        if regime == "UNKNOWN_REGIME":
            unknown_regime_rows += 1

        key = (
            fmt(row.get("strategy")),
            fmt(row.get("timeframe")),
            fmt(row.get("symbol")),
            source,
            norm_reason,
        )

        bucket = grouped[key]
        bucket["trades"] += 1
        bucket["dynamic_reason_rows"] += has_dynamic
        bucket["commission"] += float(row.get("commission") or 0.0)
        bucket["example_raw_reason"] = bucket["example_raw_reason"] or raw_reason
        bucket["param_keys"].update(params.keys())
        bucket["regimes"] = bucket.get("regimes", set())
        bucket["regimes"].add(regime)

    print("SIGNAL_CLASS_NORMALIZATION_ROWS")
    for key, data in sorted(grouped.items(), key=lambda item: (-item[1]["trades"], item[0])):
        strategy, timeframe, symbol, source, norm_reason = key
        param_keys = ",".join(sorted(data["param_keys"])) if data["param_keys"] else "NONE"
        regimes = ",".join(sorted(data.get("regimes", set()))) or "UNKNOWN_REGIME"

        print(
            "SIGNAL_CLASS_NORMALIZATION_ROW "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"symbol={symbol} "
            f"entry_source={source} "
            f"normalized_reason={norm_reason} "
            f"regimes={regimes} "
            f"trades={data['trades']} "
            f"dynamic_reason_rows={data['dynamic_reason_rows']} "
            f"param_keys={param_keys} "
            f"commission={data['commission']:.6f} "
            f"example_raw_reason={fmt(data['example_raw_reason'])}"
        )

    print()
    print("SIGNAL_CLASS_NORMALIZATION_AUDIT_SUMMARY")
    print(f"trades_total={len(rows)}")
    print(f"normalized_classes={len(grouped)}")
    print(f"dynamic_reason_rows={dynamic_rows}")
    print(f"unknown_source_rows={unknown_source_rows}")
    print(f"unknown_regime_rows={unknown_regime_rows}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("recommended_normalize_reason=1")
    print("recommended_extract_numeric_params_to_features=1")
    print("recommended_add_signal_class_field=1")

    if dynamic_rows > 0 or unknown_source_rows > 0:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_REQUIRED")
    else:
        print("VERDICT=SIGNAL_CLASS_NORMALIZATION_OK")

    print("SIGNAL_CLASS_NORMALIZATION_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
