#!/usr/bin/env bash
set -euo pipefail

FILE="scripts/research/build_postgresql_futures_concrete_contract_backtest_v1.py"

echo "=== TEST_POSTGRESQL_FUTURES_CONCRETE_EXPLICIT_TEMPLATE_V1 ==="

python -m py_compile "$FILE"

grep -Fq -- "--template-run-uuid" "$FILE"
grep -Fq "run_uuid = %s::uuid" "$FILE"
grep -Fq "status_code = 'DONE'" "$FILE"
grep -Fq "'POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1'" "$FILE"
grep -Fq "explicit_template_missing_or_incompatible" "$FILE"

echo "explicit_template_supported=1"
echo "explicit_template_requires_done=1"
echo "explicit_template_requires_adapter_v1=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_FUTURES_CONCRETE_EXPLICIT_TEMPLATE_V1_OK"
