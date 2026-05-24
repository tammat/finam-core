#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/research_pipeline_orchestrator.py

grep -q "build_trade_exit_policy_context.py" src/scripts/research_pipeline_orchestrator.py
grep -q "build_trade_context_snapshots.py" src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()

exit_pos = text.find("build_trade_exit_policy_context.py")
context_pos = text.find("build_trade_context_snapshots.py")

assert exit_pos != -1
assert context_pos != -1
assert exit_pos < context_pos

print("EXIT_POLICY_CONTEXT_BEFORE_TRADE_CONTEXT_OK")
PY

echo "RESEARCH_PIPELINE_EXIT_POLICY_CONTEXT_WIRING_OK"
