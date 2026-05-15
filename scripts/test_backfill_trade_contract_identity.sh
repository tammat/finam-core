#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/backfill_trade_contract_identity.py \
  src/finam_core/contracts/contract_identity_resolver.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/backfill_trade_contract_identity.py").read_text(encoding="utf-8")

assert "ContractIdentityResolver.resolve(symbol)" in text
assert "continuous_symbol" in text
assert "payload = payload ||" in text

print("OK: backfill trade contract identity script static check")
PY
