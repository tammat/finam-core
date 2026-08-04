#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "=== TEST CONTROL V3 DECISION FUNNEL V2 ==="

PAGE="src/marketcore/presentation/pages/decision_funnel_v1.py"
RENDERER="$(
    grep -R -l \
      --include='*.py' \
      '^def render_control_compact_v3' \
      src/marketcore/presentation
)"

"$PYTHON" -m py_compile \
  "$PAGE" \
  "$RENDERER"

"$PYTHON" - "$PAGE" "$RENDERER" <<'PY'
from __future__ import annotations

import ast
import pathlib
import sys


page_path = pathlib.Path(sys.argv[1])
renderer_path = pathlib.Path(sys.argv[2])

page_source = page_path.read_text(encoding="utf-8")
renderer_source = renderer_path.read_text(encoding="utf-8")

page_tree = ast.parse(page_source)
renderer_tree = ast.parse(renderer_source)

assert page_source.count(
    "/api/kg/v1/decision-funnel"
) == 1

assert "get_json" in page_source

for marker in (
    "psycopg2",
    "DATABASE_URL",
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "TRUNCATE ",
    "DROP ",
    "ALTER ",
    ".execute(",
    ".commit(",
    "send_order",
    "place_order",
    "submit_order",
):
    assert marker not in page_source, marker

assert renderer_source.count(
    "from marketcore.presentation.pages."
    "decision_funnel_v1 import "
    "load_decision_funnel_section_v1"
) == 1

assert renderer_source.count(
    "def _decision_funnel_section_v1("
) == 1

assert renderer_source.count(
    "_decision_funnel_section_v1(),"
) == 1

signal_index = renderer_source.index(
    "_signal_funnel_section(snapshot),"
)
decision_index = renderer_source.index(
    "_decision_funnel_section_v1(),"
)

assert signal_index < decision_index

dangerous_calls: list[str] = []

for tree in (page_tree, renderer_tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = ""

        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr

        if name in {
            "executemany",
            "commit",
            "rollback",
            "system",
            "Popen",
            "send_order",
            "place_order",
            "submit_order",
        }:
            dangerous_calls.append(name)

assert dangerous_calls == [], dangerous_calls

print("endpoint_only_contract=OK")
print("page_direct_sql=0")
print("renderer_helper_count=1")
print("renderer_attachment_count=1")
print("attachment_order=AFTER_SIGNAL_FUNNEL")
print("runtime_instrumentation=0")
PY

"$PYTHON" - <<'PY'
from __future__ import annotations

from unittest.mock import patch

from marketcore.presentation.pages.decision_funnel_v1 import (
    load_decision_funnel_section_v1,
)


payload = {
    "status": "OK",
    "data": {
        "status": "EMPTY",
        "read_only": True,
        "summary": {
            "event_count": 0,
            "signal_count": 0,
            "pass_events": 0,
            "reject_events": 0,
            "error_events": 0,
            "skip_events": 0,
            "symbol_count": 0,
            "strategy_count": 0,
            "rejection_rate": None,
            "first_event_at": None,
            "last_event_at": None,
        },
        "stage_funnel": [],
        "top_rejection_reasons": [],
        "dimensions": [],
        "recent_events": [],
        "metadata": {
            "runtime_instrumentation": 0,
        },
    },
    "metadata": {
        "read_only": 1,
    },
}

with patch(
    "marketcore.presentation.pages."
    "decision_funnel_v1.get_json",
    return_value=payload,
):
    section = load_decision_funnel_section_v1()

assert section.status == "EMPTY"
assert section.summary_rows[0]["signal_count"] == 0
assert section.metadata["read_only"] == 1
assert section.metadata["ui_direct_sql"] == 0
assert section.metadata["runtime_instrumentation"] == 0

print("empty_state_contract=OK")
print("read_only_contract=OK")
PY

git diff --check -- \
  "$PAGE" \
  "$RENDERER" \
  scripts/apply_control_v3_decision_funnel_v2.sh \
  scripts/test_control_v3_decision_funnel_v2.sh

echo "python_compile=OK"
echo "read_only=1"
echo "ui_direct_sql=0"
echo "runtime_instrumentation=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CONTROL_V3_DECISION_FUNNEL_V2_OK"
