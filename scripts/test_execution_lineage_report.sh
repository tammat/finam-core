#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/execution_lineage_report.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/execution_lineage_report.py").read_text(encoding="utf-8")

checks = [
    "requested_symbol",
    "execution_symbol",
    "continuous_symbol",
    "total_notional",
    "payload->>'execution_symbol'",
    "payload->>'requested_symbol'",
]

for c in checks:
    assert c in text, c

print("OK: execution lineage analytics static check")
PY

PYTHONPATH=src python src/scripts/execution_lineage_report.py

test -f reports/execution_lineage_report.tsv

grep -q "execution_symbol" reports/execution_lineage_report.tsv
grep -q "continuous_symbol" reports/execution_lineage_report.tsv

echo "OK: execution lineage analytics report"
