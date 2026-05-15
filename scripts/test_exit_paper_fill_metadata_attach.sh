#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "exit/hard-close PAPER fill тоже должен нести metadata" in text
assert text.count("FillMetadataFactory.attach(fill, intent=intent, market_state=st, raw_fill=raw_fill)") >= 2

print("OK: exit/hard-close PAPER fill получает metadata attach")
PY
