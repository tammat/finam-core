#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_cross_contract_liquidity_decisions.sql >/dev/null

python -m py_compile \
  src/finam_core/orderflow/cross_contract_liquidity_allocator.py \
  src/scripts/select_cross_contract_liquidity.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/select_cross_contract_liquidity.py").read_text(encoding="utf-8")

checks = [
    "cross_contract_liquidity_decisions",
    "preferred_symbol",
    "continuous_symbol",
    "candidates",
    "json.dumps",
]

for c in checks:
    assert c in text, c

print("OK: cross contract liquidity persistence static check")
PY

PYTHONPATH=src python src/scripts/select_cross_contract_liquidity.py
