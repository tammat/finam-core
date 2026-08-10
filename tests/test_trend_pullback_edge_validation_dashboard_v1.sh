#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_TREND_PULLBACK_EDGE_VALIDATION_DASHBOARD_V1 ==="

python - <<'PY'
from scripts.research.serve_multi_asset_breakout_dashboard_v1 import (
    load_trend_pullback_edge_validation_v1,
    render_trend_pullback_edge_validation_v1,
)

data = load_trend_pullback_edge_validation_v1()

if data.get("status") != "READY":
    raise SystemExit(
        "ERROR=EDGE_VALIDATION_LOAD_FAILED "
        f"status={data.get('status')} "
        f"error={data.get('error')}"
    )

rows = data.get("rows") or []

if len(rows) != 3:
    raise SystemExit(
        "ERROR=EXPECTED_3_EDGE_VALIDATION_ROWS "
        f"actual={len(rows)}"
    )

by_symbol = {
    row["symbol"]: row
    for row in rows
}

required = {
    "NVTK@MISX",
    "PLZL@MISX",
    "USDRUBF@RTSX",
}

if set(by_symbol) != required:
    raise SystemExit(
        "ERROR=UNEXPECTED_EDGE_SYMBOL_SET "
        f"symbols={sorted(by_symbol)}"
    )

for symbol in required:
    if (
        by_symbol[symbol]["robustness_status"]
        != "ROBUST"
    ):
        raise SystemExit(
            "ERROR=ROBUSTNESS_STATUS_INVALID "
            f"symbol={symbol}"
        )

for symbol in (
    "NVTK@MISX",
    "PLZL@MISX",
):
    if (
        by_symbol[symbol]["effective_cost_status"]
        != "REJECT_AFTER_BASE_COSTS"
    ):
        raise SystemExit(
            "ERROR=EQUITY_COST_STATUS_INVALID "
            f"symbol={symbol}"
        )

if (
    by_symbol["USDRUBF@RTSX"][
        "effective_cost_status"
    ]
    != "FUTURES_COST_SEMANTICS_PENDING"
):
    raise SystemExit(
        "ERROR=USDRUBF_PENDING_STATUS_INVALID"
    )

html = render_trend_pullback_edge_validation_v1()

for required_text in (
    "Валидация торгового преимущества",
    "NVTK@MISX",
    "PLZL@MISX",
    "USDRUBF@RTSX",
    "ОТКЛОНЕНО ПО COSTS",
    "ОЖИДАЕТ FUTURES COSTS",
    "НЕ ПОДТВЕРЖДЁН",
    "ЗАПРЕЩЁН",
):
    if required_text not in html:
        raise SystemExit(
            "ERROR=DASHBOARD_TEXT_MISSING "
            f"value={required_text}"
        )

print("rows=3")
print("robust=3")
print("equity_rejected=2")
print("futures_pending=1")
print("economic_edge_claimed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_TREND_PULLBACK_EDGE_VALIDATION_DASHBOARD_V1_OK"
)
PY
