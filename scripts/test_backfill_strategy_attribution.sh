#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/backfill_strategy_attribution.py \
  src/finam_core/contracts/contract_identity_resolver.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/backfill_strategy_attribution.py").read_text(encoding="utf-8")

assert "strategy_attribution_backfill_v1" in text
assert "confidence" in text
assert "continuous_symbol" in text
assert "identity.continuous if identity.is_futures else symbol" in text

print("OK: strategy attribution backfill static check")
PY
