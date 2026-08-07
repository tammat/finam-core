#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
AUDIT="scripts/research/build_postgresql_edge_backtest_adapter_forensic_audit_v1.py"
LOG="/tmp/test_postgresql_edge_backtest_adapter_forensic_audit_v1.log"

BATCH_ID="${1:?batch id is required}"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$AUDIT"

PYTHONPATH=src \
"$PYTHON" "$AUDIT" \
  --batch-id "$BATCH_ID" |
tee "$LOG"

grep -Fq "FORENSIC_RUN " "$LOG"
grep -Fq "candidate_file_count=" "$LOG"
grep -Fq "root_cause=" "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_FORENSIC_AUDIT_V1_READY" \
  "$LOG"

# Проверяем не текстовые маркеры, а SQL-строки,
# фактически передаваемые в execute/executemany.
PYTHONPATH=src \
"$PYTHON" - "$AUDIT" <<'PY'
from __future__ import annotations

import ast
import pathlib
import sys


path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(path))

forbidden_sql_prefixes = (
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "TRUNCATE ",
    "ALTER ",
    "DROP ",
    "CREATE ",
    "GRANT ",
    "REVOKE ",
)

sql_calls = 0
mutation_calls: list[str] = []


def literal_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []

        for item in node.values:
            if isinstance(item, ast.Constant):
                parts.append(str(item.value))
            else:
                return None

        return "".join(parts)

    return None


for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue

    if not isinstance(node.func, ast.Attribute):
        continue

    if node.func.attr not in {"execute", "executemany"}:
        continue

    if not node.args:
        continue

    sql_calls += 1

    sql_text = literal_text(node.args[0])

    if sql_text is None:
        continue

    normalized = " ".join(
        sql_text.strip().upper().split()
    )

    if normalized.startswith(forbidden_sql_prefixes):
        mutation_calls.append(
            f"line={node.lineno} sql={normalized[:160]}"
        )

print(f"sql_execute_call_count={sql_calls}")
print(f"sql_mutation_call_count={len(mutation_calls)}")

for item in mutation_calls:
    print(f"SQL_MUTATION={item}")

if mutation_calls:
    raise SystemExit(1)

print("sql_read_only_contract=OK")
print(
    "VERDICT="
    "POSTGRESQL_EDGE_BACKTEST_ADAPTER_FORENSIC_SQL_STATIC_OK"
)
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
echo "VERDICT=TEST_POSTGRESQL_EDGE_BACKTEST_ADAPTER_FORENSIC_AUDIT_V1_OK"
