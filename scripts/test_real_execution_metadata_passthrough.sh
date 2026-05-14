#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/execution_dispatcher.py \
  src/finam_core/execution/fill_metadata_factory.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/execution/execution_dispatcher.py").read_text(encoding="utf-8")

assert "from finam_core.execution.fill_metadata_factory import FillMetadataFactory" in text
assert "FillMetadataFactory.attach(" in text
assert "raw_fill=result" in text
assert "market_state=market_state or {}" in text

print("OK: real execution metadata passthrough is wired")
PY
