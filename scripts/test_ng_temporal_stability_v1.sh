#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_NG_TEMPORAL_STABILITY_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_ng_temporal_stability_v1.py

SYMBOL=NGN6@RTSX "$PY_BIN" src/scripts/analytics/build_ng_temporal_stability_v1.py \
  > /tmp/ng_temporal_stability_v1.out

grep -q "NG TEMPORAL STABILITY V1" /tmp/ng_temporal_stability_v1.out
grep -q "SUMMARY" /tmp/ng_temporal_stability_v1.out
grep -q "BY_WEEKDAY" /tmp/ng_temporal_stability_v1.out
grep -q "BY_HOUR_MSK" /tmp/ng_temporal_stability_v1.out
grep -q "PROFIT_CONCENTRATION" /tmp/ng_temporal_stability_v1.out
grep -q "STABILITY_SCORE" /tmp/ng_temporal_stability_v1.out
grep -q "FINAL_VERDICT" /tmp/ng_temporal_stability_v1.out

echo "TEST_NG_TEMPORAL_STABILITY_V1_OK"
