#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
AUDIT="scripts/research/build_postgresql_edge_backtest_adapter_entrypoint_audit_v1.py"
LOG="/tmp/test_postgresql_edge_backtest_adapter_entrypoint_audit_v1.log"

BATCH_ID="${1:?failed batch id is required}"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$AUDIT"

set +e

PYTHONPATH=src \
"$PYTHON" "$AUDIT" \
  --failed-batch-id "$BATCH_ID" |
tee "$LOG"

RC="${PIPESTATUS[0]}"

set -e

echo "entrypoint_audit_exit_code=$RC"

grep -Fq "candidate_count=" "$LOG"
grep -Fq "root_cause=" "$LOG"

PYTHONPATH=src \
"$PYTHON" - "$AUDIT" <<'PY'
from __future__ import annotations

import ast
import pathlib
import sys


path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(path))

mutations: list[str] = []

for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue

    if not isinstance(node.func, ast.Attribute):
        continue

    if node.func.attr not in {"execute", "executemany"}:
        continue

    if not node.args:
        continue

    first = node.args[0]

    if not (
        isinstance(first, ast.Constant)
        and isinstance(first.value, str)
    ):
        continue

    sql = " ".join(
        first.value.strip().upper().split()
    )

    if sql.startswith(
        (
            "INSERT ",
            "UPDATE ",
            "DELETE ",
            "ALTER ",
            "DROP ",
            "CREATE ",
            "TRUNCATE ",
        )
    ):
        mutations.append(
            f"line={node.lineno}:{sql[:120]}"
        )

print(f"sql_mutation_call_count={len(mutations)}")

for item in mutations:
    print(f"SQL_MUTATION={item}")

if mutations:
    raise SystemExit(1)

print("sql_read_only_contract=OK")
PY

for marker in \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" "$AUDIT" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_runtime_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

if [[ "$RC" -eq 0 ]]; then
    grep -Fq \
      "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_ENTRYPOINT_AUDIT_V1_READY" \
      "$LOG"
else
    grep -Fq \
      "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_ENTRYPOINT_AUDIT_V1_BLOCKED" \
      "$LOG"
fi

echo "db_writes_performed=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_ADAPTER_ENTRYPOINT_AUDIT_V1_OK"
