#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_FILL_PAYLOAD_SECOND_INIT_SAFE_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "payload уже инициализирован выше" in text
assert text.count('payload = getattr(fill, "payload", None)') == 1

print("TEST_FILL_PAYLOAD_SECOND_INIT_SAFE_V1_OK")
PY
