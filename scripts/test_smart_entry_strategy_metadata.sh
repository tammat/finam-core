#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "def _strategy_name_for_symbol" in text
assert '"strategy": strategy_name' in text
assert '"source": "smart_entry_retest"' in text
assert '"strategy": strategy_name' in text

print("OK: smart-entry intent содержит strategy/source metadata")
PY
