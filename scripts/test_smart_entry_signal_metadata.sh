#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert '"signal_id": f"smart-{sym}-{int(time.time() * 1000)}"' in text
assert '"horizon": "INTRADAY"' in text
assert '"timeframe": "LIVE"' in text
assert '"source": "smart_entry_retest"' in text

print("OK: smart-entry intent содержит signal metadata")
PY
