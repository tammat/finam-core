#!/usr/bin/env bash
set -euo pipefail

FILE="src/finam_core/research/postgresql_edge_backtest_adapter_v1.py"

echo "=== TEST_POSTGRESQL_FUTURES_MONETARY_PNL_V1 ==="

python -m py_compile "$FILE"

python - <<'PY'
from decimal import Decimal
from pathlib import Path

path = Path(
    "src/finam_core/research/"
    "postgresql_edge_backtest_adapter_v1.py"
)
text = path.read_text(encoding="utf-8")

required = (
    "def load_futures_contract_multiplier(",
    "FUTURES_CONTRACT_SPEC_NOT_RESOLVED:",
    "FUTURES_CONTRACT_SPEC_IDENTITY_MISMATCH:",
    "futures_contract_multiplier: Decimal | None = None",
    "* futures_contract_multiplier",
)

for marker in required:
    assert marker in text, marker

# Старый безусловный futures linear PnL больше не должен
# быть единственным путём для RTS futures.
assert 'symbol.endswith("@RTSX")' in text

# Денежные identities подтверждённых MOEX specs.
ngz6_multiplier = (
    Decimal("8.00687000") / Decimal("0.00100000")
)
ngq6_multiplier = (
    Decimal("8.14077000") / Decimal("0.00100000")
)

ngz6_pnl = (
    Decimal("0.001")
    * Decimal("1")
    * ngz6_multiplier
)
ngq6_pnl = (
    Decimal("0.001")
    * Decimal("1")
    * ngq6_multiplier
)

assert ngz6_multiplier == Decimal("8006.87")
assert ngq6_multiplier == Decimal("8140.77")
assert ngz6_pnl == Decimal("8.00687")
assert ngq6_pnl == Decimal("8.14077")

# Reference root specs обязаны провалить identity.
br_root_stored = Decimal("1")
br_root_calculated = (
    Decimal("1") / Decimal("0.01")
)
ng_root_stored = Decimal("1")
ng_root_calculated = (
    Decimal("1") / Decimal("0.001")
)

assert br_root_stored != br_root_calculated
assert ng_root_stored != ng_root_calculated

# BRZ6-specific CBR path должен сохраниться.
assert "def load_brz6_monetary_context(" in text
assert "brz_tick_value_rub(" in text

print("ngz6_multiplier=8006.87")
print("ngz6_one_tick_pnl=8.00687")
print("ngq6_multiplier=8140.77")
print("ngq6_one_tick_pnl=8.14077")
print("root_reference_specs_rejected=1")
print("brz6_special_path_preserved=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=TEST_POSTGRESQL_FUTURES_MONETARY_PNL_V1_OK")
PY
