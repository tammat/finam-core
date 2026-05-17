#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_execution_engine.py \
  src/finam_core/data/runtime_universe_provider.py

python - <<'PY'
from finam_core.runtime.runtime_execution_engine import RuntimeExecutionEngine


class LoadSymbolsProvider:
    def load_symbols(self):
        return ["SBER@MISX", "GAZP@MISX"]


class GetSymbolsProvider:
    def get_symbols(self):
        return ["LKOH@MISX"]


engine_a = RuntimeExecutionEngine(universe_provider=LoadSymbolsProvider())
assert engine_a.load_active_symbols() == ["SBER@MISX", "GAZP@MISX"]

engine_b = RuntimeExecutionEngine(universe_provider=GetSymbolsProvider())
assert engine_b.load_active_symbols() == ["LKOH@MISX"]

print("OK: RuntimeExecutionEngine v3 provider compatibility")
PY
