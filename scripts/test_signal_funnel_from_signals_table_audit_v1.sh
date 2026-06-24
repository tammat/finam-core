#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_SIGNAL_FUNNEL_FROM_SIGNALS_TABLE_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_signal_funnel_from_signals_table_audit_v1.py

src/scripts/research/build_signal_funnel_from_signals_table_audit_v1.py \
  | tee /tmp/signal_funnel_from_signals_table_audit_v1.out

grep -q "SIGNAL_FUNNEL_FROM_SIGNALS_TABLE_AUDIT_V1" /tmp/signal_funnel_from_signals_table_audit_v1.out
grep -q "SUMMARY_ROW" /tmp/signal_funnel_from_signals_table_audit_v1.out
grep -q "STRATEGY_FUNNEL_ROWS" /tmp/signal_funnel_from_signals_table_audit_v1.out
grep -q "REJECTION_REASON_ROWS" /tmp/signal_funnel_from_signals_table_audit_v1.out
grep -q "VERDICT=SIGNAL_FUNNEL_FROM_SIGNALS_TABLE_AUDIT_READY" /tmp/signal_funnel_from_signals_table_audit_v1.out

echo "TEST_SIGNAL_FUNNEL_FROM_SIGNALS_TABLE_AUDIT_V1_OK"
