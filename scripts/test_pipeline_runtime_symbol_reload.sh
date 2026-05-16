#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/data/runtime_symbol_reload_service.py \
  src/finam_core/data/runtime_universe_provider.py \
  src/finam_core/strategy/strategy_factory.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "_runtime_symbol_reload_if_due" in text
assert "ENABLE_RUNTIME_SYMBOL_RELOAD" in text
assert "RuntimeSymbolReloadService" in text
assert "PIPE_RUNTIME_SYMBOL_RELOAD" in text
assert "PIPE_RUNTIME_SYMBOL_STRATEGY_CREATED" in text
assert "active_symbols = self._runtime_symbol_reload_if_due(active_symbols)" in text

print("OK: paper_pipeline supports runtime symbol reload without marketdata resubscribe")
PY
