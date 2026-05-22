#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.trade_fill_quality_audit import (
    TradeFillQualityInput,
    audit_trade_fill_quality,
)

one_sided = audit_trade_fill_quality(
    TradeFillQualityInput(
        symbol="NGK6@RTSX",
        trade_source="paper",
        total_fills=100,
        buy_fills=0,
        sell_fills=100,
        missing_strategy=100,
        missing_timeframe=100,
        backfill_fills=100,
    )
)

assert one_sided.status == "ONE_SIDED_FILLS"
assert one_sided.reconstruction_allowed is False

ok = audit_trade_fill_quality(
    TradeFillQualityInput(
        symbol="PLZL@MISX",
        trade_source="paper",
        total_fills=100,
        buy_fills=50,
        sell_fills=50,
        missing_strategy=0,
        missing_timeframe=0,
        backfill_fills=0,
    )
)

assert ok.status == "RECONSTRUCTION_ALLOWED"
assert ok.reconstruction_allowed is True

print("TEST_TRADE_FILL_QUALITY_AUDIT_OK")
PY

python -m py_compile \
  src/finam_core/analytics/trade_fill_quality_audit.py \
  src/finam_core/analytics/trade_fill_quality_audit_repository.py \
  src/scripts/build_trade_fill_quality_audit.py
