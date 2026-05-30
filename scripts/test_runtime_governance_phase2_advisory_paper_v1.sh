#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_PHASE2_ADVISORY_PAPER_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "RUNTIME_GOVERNANCE_PHASE2_ADVISORY_ONLY" in text
assert "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_ADVISORY_CONTINUE" in text
assert "paper_only=1" in text
assert "phase2_advisory_only" in text
assert 'str(os.getenv("EXECUTION_MODE", "paper")).lower() == "paper"' in text

print("TEST_RUNTIME_GOVERNANCE_PHASE2_ADVISORY_PAPER_V1_OK")
PY
