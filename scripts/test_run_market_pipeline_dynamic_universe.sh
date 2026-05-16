#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/run_market_pipeline.py \
  src/finam_core/data/runtime_universe_provider.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_market_pipeline.py").read_text(encoding="utf-8")

assert "RuntimeUniverseProvider" in text
assert "--use-dynamic-universe" in text
assert "--dynamic-universe-limit" in text
assert "PIPE_DYNAMIC_UNIVERSE symbols=" in text
assert "PIPE_DYNAMIC_UNIVERSE_ERROR" in text
assert "RuntimeUniverseProvider(PostgresLogger()).load_symbols" in text
assert "select symbol from dynamic_watchlist" not in text

print("OK: run_market_pipeline supports dynamic universe flag")
PY
