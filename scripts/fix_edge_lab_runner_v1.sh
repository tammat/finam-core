#!/usr/bin/env bash
set -euo pipefail

echo "=== FIX_EDGE_LAB_RUNNER_V1 ==="

python - <<'PY'
from pathlib import Path

p = Path("src/scripts/build_edge_lab_runner_v1.py")
s = p.read_text(encoding="utf-8")

if "import json" not in s:
    s = s.replace("import os\n", "import os\nimport json\n")

s = s.replace(
    'run["parameter_json"],',
    'json.dumps(run["parameter_json"] or {}, ensure_ascii=False, sort_keys=True),'
)

s = s.replace(
    'print("VERDICT=EDGE_LAB_RUNNER_V1_READY")',
    '''if failed > 0:
        print("VERDICT=EDGE_LAB_RUNNER_V1_FAILED")
        raise SystemExit(1)

    print("VERDICT=EDGE_LAB_RUNNER_V1_READY")'''
)

p.write_text(s, encoding="utf-8")
PY

psql -d finam_core -c "
UPDATE analytics.edge_lab_run_v1
SET status_code='QUEUED',
    updated_at=now()
WHERE status_code='FAILED';
"

psql -d finam_core -c "
UPDATE analytics.research_queue_v1
SET status_code='QUEUED',
    updated_at=now()
WHERE status_code='FAILED';
"

PYTHONPATH=src python -m py_compile src/scripts/build_edge_lab_runner_v1.py

DATABASE_URL=postgresql:///finam_core EDGE_LAB_RUNNER_LIMIT=10 PYTHONPATH=src \
python src/scripts/build_edge_lab_runner_v1.py | tee /tmp/edge_lab_runner_fix_v1.txt

grep -q "VERDICT=EDGE_LAB_RUNNER_V1_READY" /tmp/edge_lab_runner_fix_v1.txt

obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
done_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='DONE';")
failed_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='FAILED';")

test "$obs" -gt 0
test "$done_runs" -gt 0
test "$failed_runs" = "0"

echo "observations=$obs"
echo "done_runs=$done_runs"
echo "failed_runs=$failed_runs"
echo "VERDICT=FIX_EDGE_LAB_RUNNER_V1_OK"
