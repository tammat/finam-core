#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile \
src/scripts/analytics/build_closed_trades_duplicate_audit_v1.py

python3 src/scripts/analytics/build_closed_trades_duplicate_audit_v1.py

echo TEST_CLOSED_TRADES_DUPLICATE_AUDIT_V1_OK
