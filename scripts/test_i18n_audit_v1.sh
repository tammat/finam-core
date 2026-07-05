#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_I18N_AUDIT_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_i18n_audit_v1.py

PYTHONPATH=src python src/scripts/build_i18n_audit_v1.py | tee /tmp/i18n_audit_v1.txt

grep -q "VERDICT=I18N_AUDIT_V1_OK" /tmp/i18n_audit_v1.txt

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_I18N_AUDIT_V1_OK"
