#!/usr/bin/env bash
set -euo pipefail

echo "=== FIX_EDGE_DISCOVERY_CANDIDATE_COLUMNS_V1 ==="

psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_batch_id TEXT NOT NULL DEFAULT 'DEFAULT';

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_rank INTEGER NOT NULL DEFAULT 0;

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_score NUMERIC(12,6) NOT NULL DEFAULT 0;

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS candidate_class TEXT NOT NULL DEFAULT 'UNCLASSIFIED';

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_formula_version TEXT NOT NULL DEFAULT 'UNKNOWN';
SQL

PYTHONPATH=src python -m py_compile src/scripts/build_edge_discovery_rule_rank_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_rule_rank_v1.py | tee /tmp/edge_discovery_rule_rank_fix_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_RULE_RANK_V1_READY" /tmp/edge_discovery_rule_rank_fix_v1.txt

bad_score=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE discovery_score < 0 OR discovery_score > 100;
")

test "$bad_score" = "0"

echo "bad_score_rows=$bad_score"
echo "VERDICT=FIX_EDGE_DISCOVERY_CANDIDATE_COLUMNS_V1_OK"
