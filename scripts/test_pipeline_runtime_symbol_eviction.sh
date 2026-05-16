#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "for stale_symbol in decision.removed_symbols:",
    "self.strategy_by_symbol.pop(stale_symbol, None)",
    "self.state.pop(stale_symbol, None)",
    "self._ng_strategy_by_symbol.pop(stale_symbol, None)",
    "PIPE_RUNTIME_SYMBOL_EVICT symbol=",
    "PIPE_RUNTIME_SYMBOL_EVICT_ERROR",
]

for c in checks:
    assert c in text, c

print("OK: paper_pipeline supports runtime symbol eviction")
PY
