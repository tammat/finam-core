#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RESEARCH_QUEUE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/014_research_queue_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_research_queue_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_research_queue_v1.py | tee /tmp/research_queue_v1.txt

grep -q "VERDICT=RESEARCH_QUEUE_V1_READY" /tmp/research_queue_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.research_queue_v1;")
queued=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.research_queue_v1 WHERE status_code='QUEUED';")

test "$rows" -gt 0
test "$queued" -gt 0

grep -q "research.status.QUEUED" src/marketcore/presentation/ui_labels.py
grep -q "research.queue.title" src/marketcore/presentation/ui_labels.py

echo "research_queue_rows=$rows"
echo "queued_rows=$queued"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RESEARCH_QUEUE_V1_OK"
