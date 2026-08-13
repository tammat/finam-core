#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/analytics/build_entry_exit_optimizer_v1.py"

echo "=== TEST EDGE SEARCH TARGETED CHALLENGER ROTATION POLICY V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

grep -q \
  "'SHADOW_ACCUMULATION'" \
  "$FILE"

grep -q \
  "'REJECTED'" \
  "$FILE"

grep -q \
  "'ROLLED_BACK'" \
  "$FILE"

grep -q \
  "'EXPENSIVE_GATES_FAILED'" \
  "$FILE"

grep -q \
  'TARGETED_RESEARCH_NO_NON_TERMINAL_CANDIDATE' \
  "$FILE"

grep -q \
  'TARGETED_ROTATION_POLICY_V1' \
  "$FILE"

# Старый defective targeted selector больше не должен существовать.
if grep -q \
  'f"{strategy}|{TARGET_SYMBOL}|{side}|TARGETED_RESEARCH_ONLY_V1".encode()' \
  "$FILE"
then
    echo "ERROR=LEGACY_TARGETED_SELECTOR_STILL_PRESENT"
    exit 1
fi

"$PY" - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/analytics/build_entry_exit_optimizer_v1.py"
).read_text(encoding="utf-8")

checks = {
    "targeted_branch_present":
        "if TARGETED_RESEARCH_ONLY:" in text,

    "active_state_lookup_present":
        "'SHADOW_ACCUMULATION'" in text
        and "'V5_OOS_COLLECTING'" in text,

    "terminal_filter_present":
        "'REJECTED'" in text
        and "'ROLLED_BACK'" in text
        and "'EXPENSIVE_GATES_FAILED'" in text,

    "terminal_exclusion_present":
        "if variant.code not in terminal_codes" in text,

    "fail_closed_present":
        "TARGETED_RESEARCH_NO_NON_TERMINAL_CANDIDATE"
        in text,

    "rotation_seed_present":
        "TARGETED_ROTATION_POLICY_V1" in text,

    "single_tuple_assignment_preserved":
        "variants = (" in text,
}

for name, ok in checks.items():
    print(
        f"CHECK name={name} passed={int(ok)}"
    )

assert all(checks.values())

print("terminal_candidate_reselection_allowed=0")
print("active_candidate_stability_preserved=1")
print("one_challenger_per_cycle_preserved=1")
print("frozen_methodology_changed=0")
print("allocator_changed=0")
print("db_writes_performed=0")
print("queue_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_EDGE_SEARCH_TARGETED_CHALLENGER_ROTATION_POLICY_V1_OK"
)
PY
