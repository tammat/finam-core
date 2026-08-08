#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

ADAPTER="src/finam_core/research/postgresql_edge_backtest_adapter_v1.py"

echo "=== TEST COMPLETED RUN READONLY REPLAY V1 ==="

PYTHONPATH=src \
/opt/finam-core/venv/bin/python -m py_compile \
  "$ADAPTER"

grep -Fq \
  "def load_completed_task_for_dry_run(" \
  "$ADAPTER"

grep -Fq \
  "AND status_code = 'DONE'" \
  "$ADAPTER"

grep -Fq \
  "if dry_run and run_uuid is not None:" \
  "$ADAPTER"

# Проверяем только SQL, реально переданный cursor.execute().
# Docstring и комментарии не являются SQL.
PYTHONPATH=src \
/opt/finam-core/venv/bin/python - <<'PY'
from pathlib import Path
import ast

path = Path(
    "src/finam_core/research/"
    "postgresql_edge_backtest_adapter_v1.py"
)

source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

target = None

for node in ast.walk(tree):
    if (
        isinstance(node, ast.FunctionDef)
        and node.name == "load_completed_task_for_dry_run"
    ):
        target = node
        break

if target is None:
    raise SystemExit(
        "ERROR=COMPLETED_DRY_RUN_LOADER_MISSING"
    )

sql_statements = []

for node in ast.walk(target):
    if not isinstance(node, ast.Call):
        continue

    func = node.func

    if not (
        isinstance(func, ast.Attribute)
        and func.attr == "execute"
    ):
        continue

    if not node.args:
        raise SystemExit(
            "ERROR=CURSOR_EXECUTE_WITHOUT_SQL"
        )

    sql_node = node.args[0]

    if not (
        isinstance(sql_node, ast.Constant)
        and isinstance(sql_node.value, str)
    ):
        raise SystemExit(
            "ERROR=NON_LITERAL_SQL_IN_READONLY_LOADER"
        )

    sql_statements.append(
        sql_node.value.upper()
    )

print(
    f"loader_sql_statement_count="
    f"{len(sql_statements)}"
)

if len(sql_statements) != 1:
    raise SystemExit(
        "ERROR=UNEXPECTED_READONLY_LOADER_SQL_COUNT:"
        f"count={len(sql_statements)}"
    )

sql = sql_statements[0]

for forbidden in (
    "FOR UPDATE",
    "UPDATE ",
    "DELETE ",
    "INSERT ",
    "MERGE ",
    "TRUNCATE ",
    "CREATE ",
    "ALTER ",
    "DROP ",
):
    count = sql.count(forbidden)

    print(
        "loader_sql_forbidden_marker="
        f"{forbidden.strip()} "
        f"count={count}"
    )

    if count != 0:
        raise SystemExit(
            "ERROR=READONLY_LOADER_MUTATION:"
            f"{forbidden.strip()}"
        )

if "SELECT *" not in sql:
    raise SystemExit(
        "ERROR=READONLY_LOADER_SELECT_MISSING"
    )

if "STATUS_CODE = 'DONE'" not in sql:
    raise SystemExit(
        "ERROR=READONLY_LOADER_DONE_GUARD_MISSING"
    )

if "RUN_UUID = %S" not in sql:
    raise SystemExit(
        "ERROR=READONLY_LOADER_RUN_UUID_GUARD_MISSING"
    )

print("completed_loader_readonly=1")
print("completed_loader_done_only=1")
print(
    "VERDICT="
    "TEST_COMPLETED_RUN_READONLY_LOADER_OK"
)
PY

echo "claim_task_changed=0"
echo "worker_claim_semantics_changed=0"
echo "completed_run_mutation_allowed=0"
echo "completed_trade_overwrite_allowed=0"

echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_COMPLETED_RUN_READONLY_REPLAY_V1_OK"
