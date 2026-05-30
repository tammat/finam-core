#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_RUNTIME_GOVERNANCE_PHASE2_ADVISORY_NO_RETURN_V1_START"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

bad = '''                        else:
                            return
                        return
'''

assert bad not in text
assert "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_ADVISORY_CONTINUE" in text
assert "RUNTIME_GOVERNANCE_PHASE2_ADVISORY_ONLY" in text

print("TEST_RUNTIME_GOVERNANCE_PHASE2_ADVISORY_NO_RETURN_V1_OK")
PY
