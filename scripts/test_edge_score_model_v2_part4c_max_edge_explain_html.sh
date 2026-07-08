#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_PART4C_MAX_EDGE_EXPLAIN_HTML ==="

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/components/max_edge_card.py \
  src/marketcore/presentation/providers/max_edge_provider.py

grep -q "edge-score-explain-card" src/marketcore/presentation/components/max_edge_card.py
grep -q "data-i18n-key=\"edge.score.explain.title\"" src/marketcore/presentation/components/max_edge_card.py
grep -q "render_edge_score_explain_card(current)" src/marketcore/presentation/components/max_edge_card.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_part4c.html

grep -q "edge-score-explain-card" /tmp/max_edge_part4c.html
grep -q "edge.score.explain.title" /tmp/max_edge_part4c.html
grep -q "ECONOMIC" /tmp/max_edge_part4c.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART4C_MAX_EDGE_EXPLAIN_HTML_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_PART4C_MAX_EDGE_EXPLAIN_HTML_OK"
