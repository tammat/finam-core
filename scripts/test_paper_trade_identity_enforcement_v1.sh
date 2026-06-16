#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q '"strategy": br_strategy' src/finam_core/pipelines/paper_pipeline.py
grep -q '"timeframe": br_timeframe' src/finam_core/pipelines/paper_pipeline.py
grep -q '"origin": "paper"' src/finam_core/pipelines/paper_pipeline.py
grep -q '"trade_source": "paper"' src/finam_core/pipelines/paper_pipeline.py
grep -q 'trade.strategy = br_strategy' src/finam_core/pipelines/paper_pipeline.py
grep -q 'trade.timeframe = br_timeframe' src/finam_core/pipelines/paper_pipeline.py

python3 - <<'PY'
from pathlib import Path

s = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()
start = s.index('trade.fill_id = f"paper_br_')
end = s.index('self.pg_logger.log_trade(trade)', start)
fallback_block = s[start:end]

for bad in [
    'getattr(intent, "strategy"',
    'getattr(signal, "strategy"',
    'getattr(intent, "timeframe"',
    'getattr(signal, "timeframe"',
    "UNKNOWN_STRATEGY",
    "UNKNOWN_TIMEFRAME",
]:
    if bad in fallback_block:
        raise SystemExit(f"FAIL: unsafe fallback token remains: {bad}")

print("BR_FALLBACK_IDENTITY_BLOCK_OK")
PY

echo TEST_PAPER_TRADE_IDENTITY_ENFORCEMENT_V1_OK
