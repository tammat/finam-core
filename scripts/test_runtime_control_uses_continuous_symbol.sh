#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/contracts/runtime_symbol_mapper.py \
  src/finam_core/contracts/contract_identity_resolver.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "RuntimeSymbolMapper.runtime_symbol(symbol)" in text
assert "control_symbol = RuntimeSymbolMapper.runtime_symbol(symbol)" in text
assert "(control_symbol, strategy)" in text
assert "control_symbol={control_symbol}" in text

print("OK: runtime-control uses continuous_symbol lookup key")
PY
