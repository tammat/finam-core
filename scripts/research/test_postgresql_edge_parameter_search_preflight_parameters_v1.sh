#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
FILE="scripts/research/build_postgresql_edge_parameter_search_v1.py"

cd "$ROOT"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$FILE"

grep -Fq \
  "validate_parameters," \
  "$FILE"

grep -Fq \
  "except AdapterContractError as error:" \
  "$FILE"

grep -Fq \
  "reason=INVALID_PARAMETER_CONTRACT" \
  "$FILE"

grep -Fq \
  '"parameter_json": Json(normalized_parameters)' \
  "$FILE"

PYTHONPATH=src \
"$PYTHON" - <<'PY'
from __future__ import annotations

from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    AdapterContractError,
    validate_parameters,
)


VALID_CASES = (
    (
        "ATR_IMPULSE_V1",
        {
            "atr_period": 14,
            "impulse_atr_multiplier": 1.0,
            "hold_bars": 5,
            "quantity": 1,
            "commission_per_side": 0,
            "slippage_bps": 0,
        },
    ),
    (
        "MOMENTUM_CONTINUATION_V1",
        {
            "momentum_period": 10,
            "hold_bars": 5,
            "quantity": 1,
            "commission_per_side": 0,
            "slippage_bps": 0,
        },
    ),
)

for strategy_code, parameters in VALID_CASES:
    normalized = validate_parameters(
        strategy_code,
        parameters,
    )

    print(
        "PARAMETER_PREFLIGHT "
        f"strategy={strategy_code} "
        "status=PASS "
        f"normalized_keys={','.join(sorted(normalized))}"
    )

invalid_failed = 0

try:
    validate_parameters(
        "ATR_IMPULSE_V1",
        {
            "commission_per_side": 0,
            "slippage_bps": -1,
        },
    )
except AdapterContractError as error:
    invalid_failed = 1
    print(
        "PARAMETER_PREFLIGHT "
        "strategy=ATR_IMPULSE_V1 "
        "status=REJECT "
        f"error={error}"
    )

if invalid_failed != 1:
    raise SystemExit(
        "ERROR=invalid_parameter_contract_not_rejected"
    )

print("db_writes_performed=0")
print(
    "VERDICT="
    "POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_PARAMETERS_RUNTIME_OK"
)
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_PARAMETERS_V1_OK"
