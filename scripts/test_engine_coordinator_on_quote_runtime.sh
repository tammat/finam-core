#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_ENGINE_COORDINATOR_ON_QUOTE=1

python -m py_compile \
  src/finam_core/engine/trading_engine_coordinator.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
import os
from finam_core.engine.trading_engine_coordinator import TradingEngineCoordinator

class MockKernel:
    def __init__(self):
        self.called = False

    def process_quote(self, event):
        self.called = True
        assert event["symbol"] == "BRM6@RTSX"

kernel = MockKernel()
coordinator = TradingEngineCoordinator(pipeline_kernel=kernel)

result = coordinator.on_quote({"symbol": "BRM6@RTSX", "price": 100.0})

assert os.getenv("ENABLE_ENGINE_COORDINATOR_ON_QUOTE") == "1"
assert result.quote_processed is True
assert result.errors == []
assert kernel.called is True

print("OK: engine coordinator on_quote runtime path")
PY
