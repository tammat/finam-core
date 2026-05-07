#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "EntryPointSelector" in text
assert "self.entry_point_selector = EntryPointSelector" in text
assert "PIPE_ENTRY_POINT_SELECTED" in text
assert "entry_point_selector.enrich_intent" in text

print("PIPELINE_ENTRY_POINT_SELECTOR_WIRED_OK")
PY
