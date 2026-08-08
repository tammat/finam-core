#!/usr/bin/env bash
set -euo pipefail

FILE="src/finam_core/research/postgresql_edge_backtest_adapter_v1.py"

echo "=== TEST_POSTGRESQL_EDGE_BACKTEST_FAILED_DRY_RUN_V1 ==="

python -m py_compile "$FILE"

grep -Fq \
  "AND status_code IN ('DONE', 'FAILED')" \
  "$FILE"

grep -Fq \
  "if dry_run and run_uuid is not None:" \
  "$FILE"

# Read-only replay не должен идти через claim_task.
python - <<'PY'
from pathlib import Path

text = Path(
    "src/finam_core/research/"
    "postgresql_edge_backtest_adapter_v1.py"
).read_text(encoding="utf-8")

assert "load_completed_task_for_dry_run" in text
assert "AND status_code IN ('DONE', 'FAILED')" in text

print("dry_run_failed_status_allowed=1")
print("VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_FAILED_DRY_RUN_V1_OK")
PY
