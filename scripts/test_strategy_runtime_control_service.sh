#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/strategy_runtime_control_service.py \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/contracts/runtime_symbol_mapper.py

python - <<'PY'
from pathlib import Path

service = Path("src/finam_core/runtime/strategy_runtime_control_service.py").read_text(encoding="utf-8")
pipeline = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "class StrategyRuntimeControlService" in service
assert "RuntimeSymbolMapper.runtime_symbol(symbol)" in service
assert "WHERE symbol = %s AND strategy = %s" in service
assert "(control_symbol, strategy)" in service

assert "self.strategy_runtime_control_service = StrategyRuntimeControlService(self.pg_logger)" in pipeline
assert "return service.allow_paper(symbol=symbol, qty=qty, strategy=strategy)" in pipeline

method_start = pipeline.find("def _strategy_runtime_control_allows_paper")
method_end = pipeline.find("\n    def ", method_start + 1)
method_text = pipeline[method_start:method_end]
assert "SELECT allow_trade" not in method_text
assert "RuntimeSymbolMapper" not in method_text

print("OK: StrategyRuntimeControlService extracted from paper_pipeline")
PY
