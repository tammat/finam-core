#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/scripts/build_closed_trade_reconstruction_v2.py \
  src/finam_core/analytics/closed_trade_reconstruction_v2_repository.py \
  src/finam_core/analytics/trade_fill_quality_audit.py \
  src/finam_core/analytics/trade_fill_quality_audit_repository.py

grep -q "CLOSED_TRADE_RECONSTRUCTION_V2_BLOCKED_BY_FILL_QUALITY" \
  src/scripts/build_closed_trade_reconstruction_v2.py

echo "TEST_CLOSED_TRADE_RECONSTRUCTION_V2_AUDIT_GATE_OK"
