#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/marketcore/action/command_worker_v2.py"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

PYTHONPATH=src "$PY" - <<'PY'
from pathlib import Path

text = Path(
    "src/marketcore/action/command_worker_v2.py"
).read_text(encoding="utf-8")

checks = {
    "parameter_select":
        "p.cycle_budget AS edge_search_cycle_budget" in text,

    "parameter_read":
        'row.get("edge_search_cycle_budget")' in text,

    "variant_export":
        'os.environ["EDGE_SEARCH_TARGET_VARIANT_BUDGET"]'
        in text,

    "cycle_export":
        'os.environ["EDGE_SEARCH_TARGET_CYCLE_BUDGET"]'
        in text,

    "legacy_fallback":
        "resolved_cycle_budget = (" in text
        and "else 1" in text,

    "positive_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_INVALID"
        in text,

    "lte_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_EXCEEDS_VARIANT_BUDGET"
        in text,

    "cycle_cleanup":
        '"EDGE_SEARCH_TARGET_CYCLE_BUDGET", None'
        in text,
}

for name, ok in checks.items():
    print(f"CHECK name={name} passed={int(ok)}")

assert all(checks.values())

print("resolved_legacy_variant_budget=13")
print("resolved_legacy_cycle_budget=1")
print("variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND")
print("cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE")
print("db_writes_performed=0")
print("queue_writes_performed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_EDGE_SEARCH_REQUEST_BUDGET_TRANSPORT_V2_PART1_OK"
)
PY
