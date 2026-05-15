#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/contracts/contract_identity_resolver.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "ContractIdentityResolver.resolve(fill_symbol)" in text
assert 'payload.setdefault("root_symbol", identity.root)' in text
assert 'payload.setdefault("continuous_symbol", identity.continuous)' in text
assert 'payload.setdefault("futures_month_code", identity.month_code)' in text
assert 'payload.setdefault("is_futures", identity.is_futures)' in text

print("OK: fallback fill payload contract identity enrichment exists")
PY
