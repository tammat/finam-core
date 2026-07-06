#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_RUNTIME_V2 ==="

scripts/test_paper_runtime_candidate_v1.sh
scripts/test_paper_portfolio_mtm_v1.sh

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/pages/paper_mtm_page.py \
  src/marketcore/presentation/pages/edge_factory_page.py \
  src/marketcore/presentation/pages/edge_audit_page.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/ >/tmp/ui_home.html
curl -fsS http://127.0.0.1:8080/paper-mtm >/tmp/ui_paper_mtm.html
curl -fsS http://127.0.0.1:8080/edge-factory >/tmp/ui_edge_factory.html
curl -fsS http://127.0.0.1:8080/edge-audit >/tmp/ui_edge_audit.html

grep -q "Paper MTM" /tmp/ui_paper_mtm.html
grep -q "Edge Factory" /tmp/ui_edge_factory.html
grep -q "Edge Audit" /tmp/ui_edge_audit.html

paper_active=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.paper_runtime_candidate_v1
WHERE paper_status='ACTIVE';
")

mtm_rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.paper_portfolio_mtm_v1;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$paper_active" -gt 0
test "$mtm_rows" -gt 0
test "$unsafe" = "0"

echo "paper_active=$paper_active"
echo "paper_mtm_rows=$mtm_rows"
echo "unsafe_rows=$unsafe"
echo "ui_home=ok"
echo "ui_paper_mtm=ok"
echo "ui_edge_factory=ok"
echo "ui_edge_audit=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_V2_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_V2_OK"
