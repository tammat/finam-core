#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "PIPE_FILL_METADATA_ATTACH_FAILED" in text
assert "fill.signal_id = signal_payload.get(\"signal_id\")" in text
assert "fill.payload = {" in text
assert "\"signal_id\": intent.get(\"signal_id\")" in text
assert "\"strategy\": intent.get(\"strategy\")" in text
assert "\"regime\": intent.get(\"regime\")" in text

print("OK: paper fill receives signal metadata")
PY
