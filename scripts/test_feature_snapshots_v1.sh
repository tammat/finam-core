#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/features/market_feature_snapshot.py \
  src/scripts/features/build_market_feature_snapshots.py

python - <<'PY'
from finam_core.features.market_feature_snapshot import (
    normalize_root_symbol,
    classify_volatility,
    classify_trend,
    classify_range,
    classify_session_state,
    calculate_snapshot_quality,
)

assert normalize_root_symbol("NGM6@RTSX") == "NG"
assert normalize_root_symbol("BRM6@RTSX") == "BR"
assert normalize_root_symbol("GDM6@RTSX") == "GOLD"
assert normalize_root_symbol("SVM6@RTSX") == "SILVER"
assert normalize_root_symbol("CNYRUB_TOM@MISX") == "CNY"

assert classify_volatility(0.0001) == "low"
assert classify_volatility(0.0010) == "normal"
assert classify_volatility(0.0030) == "high"

assert classify_trend(0.002) == "up"
assert classify_trend(-0.002) == "down"
assert classify_trend(0.0) == "flat"

assert classify_range(0.003, 0.001) == "impulse"
assert classify_range(0.0001, 0.001) == "compression"

assert classify_session_state(5) == "MOEX_MORNING"
assert classify_session_state(10) == "MOEX_DAY"
assert classify_session_state(18) == "MOEX_EVENING"

quality, reason = calculate_snapshot_quality(
    intermarket_risk_mode="MIXED",
    intermarket_commodity_mode="LOW_IMPULSE",
    atr_proxy=0.001,
)
assert quality == "FULL"

print("FEATURE_SNAPSHOTS_V1_UNIT_OK")
PY

grep -q "feature_snapshots" scripts/migrate_feature_snapshots_v1.sh
grep -q "FEATURE_SNAPSHOTS_BUILD_OK" src/scripts/features/build_market_feature_snapshots.py

echo "FEATURE_SNAPSHOTS_V1_TEST_OK"
