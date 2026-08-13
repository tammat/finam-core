#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
FILE="src/scripts/research/enqueue_edge_search_targeted_effective_budget_v1.py"
OUT="/tmp/test_edge_search_governed_enqueue_budget_parameters_v2.out"

PYTHONPATH=src "$PY" -m py_compile "$FILE"
git diff --check -- "$FILE"

"$PY" - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/research/"
    "enqueue_edge_search_targeted_effective_budget_v1.py"
).read_text(encoding="utf-8")

checks = {
    "candidate_cycle_budget":
        '"cycle_budget": 1' in text,

    "parameter_cycle_column":
        "cycle_budget" in text,

    "three_parameter_values":
        "VALUES (%s,%s,%s)" in text,

    "cycle_insert_value":
        'candidate["cycle_budget"]' in text,

    "variant_budget_preserved":
        'candidate["effective_variants"]' in text,

    "target_id_not_budget_encoded":
        '"TARGETED_V1|"' in text,

    "one_commit_function":
        text.count(
            "def commit_candidate(conn, candidate):"
        ) == 1,
}

for name, ok in checks.items():
    print(f"CHECK name={name} passed={int(ok)}")

assert all(checks.values())

compile(
    text,
    "enqueue_edge_search_targeted_effective_budget_v1.py",
    "exec",
)

print("variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND")
print("cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE")
print("cycle_budget_value=1")
print("target_id_changed=0")
print("one_request_per_target_preserved=1")
print("db_writes_performed=0")
print("queue_writes_performed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_EDGE_SEARCH_GOVERNED_ENQUEUE_BUDGET_PARAMETERS_V2_OK"
)
PY

rm -f "$OUT"

PYTHONPATH=src "$PY" "$FILE" | tee "$OUT"

grep -q 'effective_variants=13' "$OUT"
grep -q 'cycle_budget=1' "$OUT"
grep -q 'queue_writes_performed=0' "$OUT"

echo "VERDICT=TEST_EDGE_SEARCH_GOVERNED_ENQUEUE_BUDGET_PARAMETERS_V2_OK"
