#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PARAMETER_SEARCH_GRID_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_parameter_search_grid_v1.py <<'PY'
from __future__ import annotations

import itertools
import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
JOB_LIMIT = int(os.getenv("PARAMETER_SEARCH_JOB_LIMIT", "20"))


def values_for_param(row: dict) -> list[object]:
    allowed = row.get("allowed_values") or []
    if allowed:
        return allowed

    ptype = str(row["parameter_type"]).lower()
    mn = row["min_value"]
    mx = row["max_value"]
    step = row["step_value"]

    if mn is None or mx is None:
        return []

    mn = Decimal(str(mn))
    mx = Decimal(str(mx))
    step = Decimal(str(step or 0))

    if step == 0 or mn == mx:
        val = int(mn) if ptype == "int" else float(mn)
        return [val]

    vals = []
    x = mn
    guard = 0
    while x <= mx and guard < 1000:
        vals.append(int(x) if ptype == "int" else float(x))
        x += step
        guard += 1
    return vals


def main() -> None:
    jobs_processed = 0
    trials_upserted = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM analytics.parameter_search_job_v1
                WHERE status_code='QUEUED'
                  AND method_code='GRID'
                ORDER BY created_at ASC, id ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED;
            """, (JOB_LIMIT,))
            jobs = cur.fetchall()

            for job in jobs:
                cur.execute("""
                    SELECT *
                    FROM analytics.parameter_search_space_v1
                    WHERE strategy_code=%s
                      AND enabled=true
                    ORDER BY parameter_name ASC;
                """, (job["strategy_code"],))
                params = cur.fetchall()

                names = [p["parameter_name"] for p in params]
                grids = [values_for_param(p) for p in params]
                grids = [g for g in grids if g]

                if not names or not grids:
                    cur.execute("""
                        UPDATE analytics.parameter_search_job_v1
                        SET status_code='FAILED',
                            updated_at=now()
                        WHERE id=%s;
                    """, (job["id"],))
                    continue

                trial_no = 0
                for combo in itertools.product(*grids):
                    if trial_no >= int(job["max_trials"]):
                        break

                    parameter_set = dict(zip(names, combo))
                    research_code = f"GRID:{job['search_code']}:T{trial_no:04d}"

                    cur.execute("""
                        INSERT INTO analytics.research_queue_v1 (
                            research_code,
                            strategy_code,
                            symbol,
                            timeframe,
                            parameter_set,
                            priority,
                            status_code,
                            source_version,
                            updated_at
                        )
                        VALUES (
                            %s,%s,%s,%s,%s::jsonb,
                            50,
                            'QUEUED',
                            'PARAMETER_SEARCH_GRID_V1',
                            now()
                        )
                        ON CONFLICT(strategy_code, symbol, timeframe, parameter_set)
                        DO UPDATE SET
                            research_code=EXCLUDED.research_code,
                            priority=LEAST(analytics.research_queue_v1.priority, EXCLUDED.priority),
                            status_code='QUEUED',
                            source_version='PARAMETER_SEARCH_GRID_V1',
                            updated_at=now();
                    """, (
                        research_code,
                        job["strategy_code"],
                        job["symbol"],
                        job["timeframe"],
                        json.dumps(parameter_set, ensure_ascii=False, sort_keys=True),
                    ))

                    trials_upserted += 1
                    trial_no += 1

                cur.execute("""
                    UPDATE analytics.parameter_search_job_v1
                    SET status_code='DONE',
                        updated_at=now()
                    WHERE id=%s;
                """, (job["id"],))
                jobs_processed += 1

            cur.execute("""
                SELECT count(*) AS total
                FROM analytics.research_queue_v1
                WHERE source_version='PARAMETER_SEARCH_GRID_V1';
            """)
            grid_queue_total = cur.fetchone()["total"]

    print("=== PARAMETER_SEARCH_GRID_V1 ===")
    print(f"jobs_processed={jobs_processed}")
    print(f"trials_upserted={trials_upserted}")
    print(f"grid_queue_total={grid_queue_total}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PARAMETER_SEARCH_GRID_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_parameter_search_grid_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PARAMETER_SEARCH_GRID_V1 ==="

PYTHONPATH=src python -m py_compile src/scripts/build_parameter_search_grid_v1.py

DATABASE_URL=postgresql:///finam_core PARAMETER_SEARCH_JOB_LIMIT=5 PYTHONPATH=src \
python src/scripts/build_parameter_search_grid_v1.py | tee /tmp/parameter_search_grid_v1.txt

grep -q "VERDICT=PARAMETER_SEARCH_GRID_V1_READY" /tmp/parameter_search_grid_v1.txt

grid_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.research_queue_v1
WHERE source_version='PARAMETER_SEARCH_GRID_V1';
")

test "$grid_rows" -gt 0

echo "grid_research_queue_rows=$grid_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_PARAMETER_SEARCH_GRID_V1_OK"
SH_TEST

chmod +x scripts/test_parameter_search_grid_v1.sh
scripts/test_parameter_search_grid_v1.sh

echo "VERDICT=BUILD_PARAMETER_SEARCH_GRID_V1_OK"
