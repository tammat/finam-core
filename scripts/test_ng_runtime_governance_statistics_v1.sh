#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_NG_RUNTIME_GOVERNANCE_STATISTICS_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py

SYMBOL=NGN6@RTSX "$PY_BIN" src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py \
  > /tmp/ng_runtime_governance_statistics_v1.out

grep -q "NG RUNTIME GOVERNANCE STATISTICS V1" /tmp/ng_runtime_governance_statistics_v1.out
grep -q "SUMMARY" /tmp/ng_runtime_governance_statistics_v1.out
grep -q "PERFORMANCE_ALL" /tmp/ng_runtime_governance_statistics_v1.out
grep -q "PERFORMANCE_WITHOUT_BATCH_QTY_GT_1" /tmp/ng_runtime_governance_statistics_v1.out
grep -q "PERFORMANCE_QTY_EQ_1" /tmp/ng_runtime_governance_statistics_v1.out
grep -q "PERFORMANCE_QTY_GT_1" /tmp/ng_runtime_governance_statistics_v1.out
grep -q "BY_HOUR_MSK" /tmp/ng_runtime_governance_statistics_v1.out
grep -q "VERDICT" /tmp/ng_runtime_governance_statistics_v1.out

echo "TEST_NG_RUNTIME_GOVERNANCE_STATISTICS_V1_OK"
