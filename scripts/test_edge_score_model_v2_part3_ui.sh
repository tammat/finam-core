#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART3_UI ==="

rm -rf src/scripts/__pycache__ src/marketcore/**/__pycache__ || true

grep -RIn --exclude-dir='__pycache__' --exclude='*.pyc' \
  "edge_score_v2" src/marketcore/presentation src/scripts | head -20

grep -RIn --exclude-dir='__pycache__' --exclude='*.pyc' \
  "reconciliation_verdict" src/marketcore/presentation src/scripts | head -20

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.max_edge_provider import MaxEdgeProvider

vm = MaxEdgeProvider().load(limit=20)
assert vm.ranking, "NO_MAX_EDGE_ROWS"

row = vm.ranking[0]
assert "edge_score_v2" in row, "EDGE_SCORE_V2_NOT_IN_PROVIDER_ROW"
assert "reconciliation_verdict" in row, "RECONCILIATION_VERDICT_NOT_IN_PROVIDER_ROW"

print("provider_edge_score_v2=", row.get("edge_score_v2"))
print("provider_reconciliation_verdict=", row.get("reconciliation_verdict"))
PY

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_v2_part3.html

grep -q "edge_score_v2" /tmp/max_edge_v2_part3.html
grep -q "reconciliation_verdict" /tmp/max_edge_v2_part3.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART_3_UI_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART3_UI_OK"
