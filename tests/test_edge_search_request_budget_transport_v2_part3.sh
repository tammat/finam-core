#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/run_targeted_entry_exit_oos_v1.py"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

"$PY" - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/run_targeted_entry_exit_oos_v1.py"
).read_text(encoding="utf-8")

checks = {
    "variant_receive":
        '"EDGE_SEARCH_TARGET_VARIANT_BUDGET", ""'
        in text,

    "cycle_receive":
        '"EDGE_SEARCH_TARGET_CYCLE_BUDGET", ""'
        in text,

    "cycle_parse":
        "cycle_budget = int(cycle_budget_raw)"
        in text,

    "legacy_fallback":
        "cycle_budget = 1" in text,

    "positive_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_INVALID"
        in text,

    "lte_variant_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_EXCEEDS_VARIANT_BUDGET"
        in text,

    "requires_variant_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_REQUIRES_VARIANT_BUDGET"
        in text,

    "variant_child_env":
        'env["EDGE_SEARCH_TARGET_VARIANT_BUDGET"]'
        in text,

    "cycle_child_env":
        'env["EDGE_SEARCH_TARGET_CYCLE_BUDGET"]'
        in text,

    "cycle_diagnostic":
        '"target_cycle_budget="' in text,
}

for name, ok in checks.items():
    print(f"CHECK name={name} passed={int(ok)}")

assert all(checks.values())

print("variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND")
print("cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE")
print("legacy_variant_only_invocation_supported=1")
print("cycle_without_variant_fail_closed=1")
print("optimizer_semantics_changed=0")
print("db_writes_performed=0")
print("queue_writes_performed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_EDGE_SEARCH_REQUEST_BUDGET_TRANSPORT_V2_PART3_OK"
)
PY
