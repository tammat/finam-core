#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/strategy/dynamic_strategy_resolver.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

start = text.find("def _strategy_name_for_symbol")
end = text.find("\n    def ", start + 1)

assert start != -1
assert end != -1

block = text[start:end]

assert "DynamicStrategyResolver" in block
assert "strategy_for_symbol(symbol)" in block
assert "PIPE_DYNAMIC_STRATEGY_RESOLVER_ERROR" in block
assert "SYMBOL_STRATEGY_MAP.get(symbol, DEFAULT_STRATEGY)" in block

print("OK: paper_pipeline resolves strategy from dynamic_watchlist with fallback")
PY
