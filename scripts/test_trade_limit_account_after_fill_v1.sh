#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_TRADE_LIMIT_ACCOUNT_AFTER_FILL_V1_START"

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/runtime/trade_gate_service.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "trade_gate.account_trade(sym)" not in text
assert "def _account_trade_after_fill_v1" in text
assert "trade_gate.account_trade(str(symbol))" in text
assert 'self.bus.publish({"type": "FILL", "fill": fill})' in text
assert 'self._account_trade_after_fill_v1(intent.get("symbol"))' in text

print("TEST_TRADE_LIMIT_ACCOUNT_AFTER_FILL_V1_OK")
PY
