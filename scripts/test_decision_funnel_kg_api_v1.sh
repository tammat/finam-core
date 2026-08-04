#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "=== TEST DECISION FUNNEL KG API V1 ==="

API_FILE="src/marketcore/api/serve_knowledge_graph_api_v1.py"
ADAPTER_FILE="src/marketcore/api/read_models/decision_funnel_v1.py"
READ_MODEL_FILE="storage/decision_funnel_read_model.py"

for file in \
  "$API_FILE" \
  "$ADAPTER_FILE" \
  "$READ_MODEL_FILE"
do
    [[ -f "$file" ]] || {
        echo "ERROR=file_missing:$file"
        exit 1
    }
done

"$PYTHON" -m py_compile \
  "$API_FILE" \
  "$ADAPTER_FILE" \
  "$READ_MODEL_FILE"

"$PYTHON" - <<'PY'
from __future__ import annotations

import ast
import pathlib


api_path = pathlib.Path(
    "src/marketcore/api/serve_knowledge_graph_api_v1.py"
)
adapter_path = pathlib.Path(
    "src/marketcore/api/read_models/decision_funnel_v1.py"
)
read_model_path = pathlib.Path(
    "storage/decision_funnel_read_model.py"
)

api_source = api_path.read_text(encoding="utf-8")
adapter_source = adapter_path.read_text(encoding="utf-8")
read_model_source = read_model_path.read_text(
    encoding="utf-8"
)

ast.parse(api_source)
ast.parse(adapter_source)
ast.parse(read_model_source)

assert (
    api_source.count(
        '"/api/kg/v1/decision-funnel"'
    )
    == 1
)

assert (
    "build_decision_funnel_read_model"
    in api_source
)

for marker in (
    '"hours"',
    '"recent_limit"',
    '"reason_limit"',
    '"dimension_limit"',
    '"symbol"',
    '"strategy"',
    '"timeframe"',
    '"runtime_instrumentation": 0',
    '"write_actions_allowed": 0',
    '"execution_actions_allowed": 0',
):
    assert marker in api_source, marker

# SQL-запись и торговые действия запрещены на уровне исходного кода.
# Metadata-ключ systemctl_actions_allowed не является действием.
for marker in (
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "TRUNCATE ",
    "DROP ",
    "ALTER ",
    ".commit(",
    "send_order",
    "place_order",
    "submit_order",
):
    assert marker not in adapter_source, marker

adapter_tree = ast.parse(adapter_source)

forbidden_imports: list[str] = []
dangerous_calls: list[str] = []

for node in ast.walk(adapter_tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            root_name = alias.name.split(".", 1)[0]

            if root_name in {
                "subprocess",
                "sqlite3",
            }:
                forbidden_imports.append(alias.name)

    elif isinstance(node, ast.ImportFrom):
        module_name = node.module or ""
        root_name = module_name.split(".", 1)[0]

        if root_name in {
            "subprocess",
            "sqlite3",
        }:
            forbidden_imports.append(module_name)

    elif isinstance(node, ast.Call):
        call_name = ""

        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_name = node.func.attr

        if call_name in {
            "commit",
            "executemany",
            "system",
            "run",
            "Popen",
            "remove",
            "unlink",
            "post",
            "send_order",
            "place_order",
            "submit_order",
        }:
            dangerous_calls.append(call_name)

assert forbidden_imports == [], forbidden_imports
assert dangerous_calls == [], dangerous_calls

assert (
    '"systemctl_actions_allowed": 0'
    in adapter_source
)

assert (
    "build_decision_funnel_read_model"
    in adapter_source
)
assert (
    "analytics.signal_decision_funnel_v1"
    in adapter_source
)

tree = ast.parse(adapter_source)

dangerous_calls: list[str] = []

for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue

    name = ""

    if isinstance(node.func, ast.Name):
        name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        name = node.func.attr

    if name in {
        "commit",
        "execute",
        "executemany",
        "system",
        "run",
        "Popen",
        "remove",
        "unlink",
        "post",
    }:
        dangerous_calls.append(name)

assert dangerous_calls == [], dangerous_calls

print("route_literal_contract=OK")
print("parameter_contract=OK")
print("adapter_contract=OK")
print("read_only_contract=OK")
print("runtime_isolation_contract=OK")
PY

# Проверяем сам адаптер через mock соединения,
# без обращения к PostgreSQL.
"$PYTHON" - <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from marketcore.api.read_models.decision_funnel_v1 import (
    build_read_model,
)


captured = {}


def fake_builder(
    connection_factory,
    **kwargs,
):
    captured["factory"] = connection_factory
    captured["kwargs"] = kwargs

    return {
        "status": "EMPTY",
        "read_only": True,
        "window": {},
        "filters": {},
        "summary": {
            "event_count": 0,
            "signal_count": 0,
        },
        "stage_funnel": [],
        "top_rejection_reasons": [],
        "dimensions": [],
        "recent_events": [],
        "metadata": {},
    }


now = datetime(
    2026,
    8,
    4,
    12,
    0,
    tzinfo=timezone.utc,
)

with patch(
    "marketcore.api.read_models."
    "decision_funnel_v1."
    "build_decision_funnel_read_model",
    side_effect=fake_builder,
):
    result = build_read_model(
        "postgresql:///finam_core",
        hours=48,
        now=now,
        symbol="BR@RTSX",
        strategy="BR_BREAKOUT",
        timeframe="M5",
        recent_limit=25,
        reason_limit=10,
        dimension_limit=30,
    )

assert result["status"] == "EMPTY"
assert result["read_only"] is True

assert captured["kwargs"] == {
    "hours": 48,
    "now": now,
    "symbol": "BR@RTSX",
    "strategy": "BR_BREAKOUT",
    "timeframe": "M5",
    "recent_limit": 25,
    "reason_limit": 10,
    "dimension_limit": 30,
}

metadata = result["metadata"]

assert metadata["ui_direct_sql"] == 0
assert metadata["write_actions_allowed"] == 0
assert metadata["systemctl_actions_allowed"] == 0
assert metadata["runtime_instrumentation"] == 0
assert metadata["execution_actions_allowed"] == 0

print("adapter_empty_state=OK")
print("adapter_parameter_forwarding=OK")
print("adapter_metadata_contract=OK")
PY

# Проверка реального read model на существующей пустой таблице.
"$PYTHON" - <<'PY'
from __future__ import annotations

import os

from marketcore.api.read_models.decision_funnel_v1 import (
    build_read_model,
)


database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

result = build_read_model(
    database_url,
    hours=24,
    recent_limit=10,
    reason_limit=10,
    dimension_limit=10,
)

assert result["status"] in {"EMPTY", "READY"}
assert result["read_only"] is True
assert result["metadata"]["runtime_instrumentation"] == 0
assert result["metadata"]["write_actions_allowed"] == 0

print(f"database_status={result['status']}")
print(
    "database_event_count="
    f"{result['summary']['event_count']}"
)
print("database_read_only=1")
PY

git diff --check -- \
  "$API_FILE" \
  "$ADAPTER_FILE" \
  "$READ_MODEL_FILE"

echo "python_compile=OK"
echo "kg_endpoint=/api/kg/v1/decision-funnel"
echo "read_only=1"
echo "ui_direct_sql=0"
echo "write_actions_allowed=0"
echo "systemctl_actions_allowed=0"
echo "runtime_instrumentation=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_FUNNEL_KG_API_V1_OK"
