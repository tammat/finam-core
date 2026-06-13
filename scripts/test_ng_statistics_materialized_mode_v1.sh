#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_NG_STATISTICS_MATERIALIZED_MODE_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py

USE_MATERIALIZED_CLOSED_TRADES=1 SYMBOL=NGN6@RTSX \
"$PY_BIN" src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py \
  > /tmp/ng_statistics_materialized_mode_v1.out

grep -q "source=analytics_closed_trades_v1" /tmp/ng_statistics_materialized_mode_v1.out
grep -q "PERFORMANCE_ALL" /tmp/ng_statistics_materialized_mode_v1.out
grep -q "VERDICT" /tmp/ng_statistics_materialized_mode_v1.out

echo "TEST_NG_STATISTICS_MATERIALIZED_MODE_V1_OK"
