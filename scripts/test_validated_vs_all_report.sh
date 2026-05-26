#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/validated_vs_all_report.py

python - <<'PY'
from finam_core.analytics.validated_vs_all_report import compare_validated_vs_all

stats = compare_validated_vs_all(
    all_pnl=[10, -5, 20, -1],
    validated_pnl=[10, 20],
    rejected_pnl=[-5, -1],
)

by_name = {x.name: x for x in stats}

assert by_name["ALL"].trades == 4
assert by_name["ALL"].net_pnl == 24
assert by_name["VALIDATED_ONLY"].trades == 2
assert by_name["VALIDATED_ONLY"].winrate == 1.0
assert by_name["REJECTED"].net_pnl == -6
assert by_name["REJECTED"].max_consecutive_losses == 2

print("VALIDATED_VS_ALL_REPORT_OK")
PY
