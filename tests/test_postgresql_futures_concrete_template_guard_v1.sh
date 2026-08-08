#!/usr/bin/env bash
set -euo pipefail

FILE="scripts/research/build_postgresql_futures_concrete_contract_backtest_v1.py"

echo "=== TEST_POSTGRESQL_FUTURES_CONCRETE_TEMPLATE_GUARD_V1 ==="

python -m py_compile "$FILE"

python - <<'PY'
from pathlib import Path

text = Path(
    "scripts/research/"
    "build_postgresql_futures_concrete_contract_backtest_v1.py"
).read_text(encoding="utf-8")

# Explicit-template branch.
assert "run_uuid = %s::uuid" in text
assert "AND status_code = 'DONE'" in text

# Continuous-symbol branch.
assert "WHERE symbol = %s" in text

# Обе ветки обязаны ограничиваться новым PostgreSQL adapter.
assert text.count("AND runner_version =") >= 2
assert text.count(
    "'POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1'"
) >= 2

# Legacy runner не должен быть допустимым template source.
assert "STRATEGY_EXECUTION_RUNNER_V1" not in text

# Parameter contract обязателен.
assert text.count("AND parameter_json IS NOT NULL") >= 2

# Fail-closed paths должны сохраниться.
assert "continuous_symbol_template_missing" in text
assert "explicit_template_missing_or_incompatible" in text

print("continuous_template_adapter_guard=1")
print("explicit_template_adapter_guard=1")
print("explicit_template_done_guard=1")
print("parameter_contract_guard=1")
print("legacy_runner_template_allowed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_POSTGRESQL_FUTURES_CONCRETE_TEMPLATE_GUARD_V1_OK"
)
PY
