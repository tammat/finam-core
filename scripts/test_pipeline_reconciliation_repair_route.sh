#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert "self.portfolio_reconciliation_repair.evaluate" in text
assert "ALLOW_PORTFOLIO_REPAIR" in text
assert "PIPE_PORTFOLIO_RECONCILIATION_REPAIRED" in text

print("OK: pipeline reconciliation repair route is wired")
PY
