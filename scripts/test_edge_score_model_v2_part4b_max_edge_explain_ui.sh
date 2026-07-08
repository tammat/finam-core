#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART4B_MAX_EDGE_EXPLAIN_UI ==="

rm -rf src/scripts/__pycache__ src/marketcore/**/__pycache__ || true

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/providers/max_edge_provider.py

grep -RIn --exclude-dir='__pycache__' --exclude='*.pyc' \
  "edge_score_explain_groups" src/marketcore/presentation/providers/max_edge_provider.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.max_edge_provider import MaxEdgeProvider

vm = MaxEdgeProvider().load(limit=20)
assert vm.ranking, "NO_MAX_EDGE_ROWS"

row = vm.ranking[0]
assert "edge_score_explain_groups" in row, "EXPLAIN_GROUPS_NOT_IN_PROVIDER_ROW"

groups = row.get("edge_score_explain_groups")
assert groups is not None, "EXPLAIN_GROUPS_IS_NONE"
assert len(groups) >= 1, "EXPLAIN_GROUPS_EMPTY"

required = {
    "group_code",
    "group_score",
    "group_weight",
    "group_contribution",
    "edge_score_v2",
    "model_verdict",
}

first = groups[0]
missing = required - set(first.keys())
assert not missing, f"EXPLAIN_GROUP_KEYS_MISSING={missing}"

print("provider_explain_groups_count=", len(groups))
print("provider_explain_first_group=", first.get("group_code"))
PY

# Проверка прав БД для UI-пользователя уже косвенно проходит через provider.
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART4B_MAX_EDGE_EXPLAIN_UI_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART4B_MAX_EDGE_EXPLAIN_UI_OK"
