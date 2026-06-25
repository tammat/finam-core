#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_UNIVERSE_DATA_COVERAGE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_universe_data_coverage_audit_v1.py

src/scripts/research/build_universe_data_coverage_audit_v1.py \
  | tee /tmp/universe_data_coverage_audit_v1.out

grep -q "UNIVERSE_DATA_COVERAGE_AUDIT_V1" /tmp/universe_data_coverage_audit_v1.out
grep -q "FUTURES_COVERAGE" /tmp/universe_data_coverage_audit_v1.out
grep -q "FUTURES_ROW name=BRENT" /tmp/universe_data_coverage_audit_v1.out
grep -q "FUTURES_ROW name=NATURAL_GAS" /tmp/universe_data_coverage_audit_v1.out
grep -q "EQUITY_COVERAGE" /tmp/universe_data_coverage_audit_v1.out
grep -q "EQUITY_ROW ticker=SBER" /tmp/universe_data_coverage_audit_v1.out
grep -q "CONTEXT_COVERAGE" /tmp/universe_data_coverage_audit_v1.out
grep -q "closed_trades_usable=" /tmp/universe_data_coverage_audit_v1.out
grep -q "feature_rows_usable=" /tmp/universe_data_coverage_audit_v1.out
grep -q "VERDICT=UNIVERSE_DATA_COVERAGE_AUDIT_READY" /tmp/universe_data_coverage_audit_v1.out

echo "TEST_UNIVERSE_DATA_COVERAGE_AUDIT_V1_OK"
