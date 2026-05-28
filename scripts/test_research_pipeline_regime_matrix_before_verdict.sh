#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/scripts/research_pipeline_orchestrator.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/research_pipeline_orchestrator.py").read_text()
matrix_pos = text.index("build_strategy_regime_matrix.py")
verdict_pos = text.index("build_strategy_research_verdict.py")

assert matrix_pos < verdict_pos, "strategy_regime_matrix must run before strategy_research_verdict"
print("RESEARCH_PIPELINE_REGIME_MATRIX_BEFORE_VERDICT_ORDER_OK")
PY

echo "RESEARCH_PIPELINE_REGIME_MATRIX_BEFORE_VERDICT_TEST_OK"
