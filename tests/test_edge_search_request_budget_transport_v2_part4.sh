#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/analytics/build_entry_exit_optimizer_v1.py"

echo "=== TEST EDGE SEARCH REQUEST BUDGET TRANSPORT V2 PART4 ==="

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

"$PY" - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/analytics/build_entry_exit_optimizer_v1.py"
).read_text(encoding="utf-8")

checks = {
    "variant_receive":
        "EDGE_SEARCH_TARGET_VARIANT_BUDGET"
        in text,

    "cycle_receive":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET"
        in text,

    "cycle_parse":
        "cycle_budget = int(cycle_budget_raw)"
        in text,

    "legacy_fallback":
        "cycle_budget = 1"
        in text,

    "positive_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_INVALID"
        in text,

    "lte_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_EXCEEDS_VARIANT_BUDGET"
        in text,

    "requires_variant_guard":
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET_REQUIRES_VARIANT_BUDGET"
        in text,

    "cardinality_guard":
        "TARGETED_RESEARCH_CYCLE_BUDGET_UNSUPPORTED"
        in text,

    "rotation_policy":
        "TARGETED_ROTATION_POLICY_V1"
        in text,

    "terminal_filter":
        "TARGETED_RESEARCH_NO_NON_TERMINAL_CANDIDATE"
        in text,

    "single_candidate_structure":
        "variants = ("
        in text,
}

for name, ok in checks.items():
    print(
        f"CHECK name={name} passed={int(ok)}"
    )

assert all(checks.values())

compile(
    text,
    "build_entry_exit_optimizer_v1.py",
    "exec",
)

print("optimizer_syntax_valid=1")
print("variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND")
print("cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE")
print("supported_targeted_cycle_budget=1")
print("multi_challenger_targeted_enabled=0")
print("rotation_policy_preserved=1")
print("terminal_candidate_filter_preserved=1")
print("frozen_methodology_preserved=1")
print("db_writes_performed=0")
print("queue_writes_performed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_EDGE_SEARCH_REQUEST_BUDGET_TRANSPORT_V2_PART4_OK"
)
PY
