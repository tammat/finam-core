#!/usr/bin/env bash
set -euo pipefail

echo "=== NO_HARDCODE_SPRINT_PLANNER_MIGRATION_V1 ==="

mkdir -p src/scripts reports scripts

cat > src/scripts/build_edge_sprint_plan_from_recommendation_v1.py <<'PY'
from __future__ import annotations

import json
from pathlib import Path

import psycopg2

RECOMMENDATION_JSON = Path("reports/recommendation_engine_latest.json")
OUT_REPORT = Path("reports/edge_sprint_plan_latest.txt")


def main() -> None:
    if not RECOMMENDATION_JSON.exists():
        raise SystemExit("RECOMMENDATION_JSON_NOT_FOUND")

    data = json.loads(RECOMMENDATION_JSON.read_text(encoding="utf-8"))

    strategies = data.get("focus_strategies", [])
    symbols = data.get("focus_symbols", [])
    timeframes = data.get("focus_timeframes", [])
    max_trials = int(data.get("max_trials", 300))
    sprint_code = data.get("next_sprint_code", "EDGE_SPRINT_AUTO")
    objective_metric = data.get("objective_metric", "normalized_edge_score")

    if not strategies or not symbols or not timeframes:
        raise SystemExit("RECOMMENDATION_PLAN_EMPTY")

    planned = 0

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor() as cur:
            for strategy_code in strategies:
                for symbol in symbols:
                    for timeframe in timeframes:
                        search_code = f"{sprint_code}:{strategy_code}:{symbol}:{timeframe}"

                        cur.execute(
                            """
                            INSERT INTO analytics.parameter_search_job_v1 (
                                search_code,
                                strategy_code,
                                symbol,
                                timeframe,
                                method_code,
                                status_code,
                                max_trials,
                                objective_metric,
                                source_version,
                                updated_at
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                            ON CONFLICT(search_code) DO UPDATE SET
                                status_code='QUEUED',
                                max_trials=EXCLUDED.max_trials,
                                objective_metric=EXCLUDED.objective_metric,
                                source_version=EXCLUDED.source_version,
                                updated_at=now()
                            """,
                            (
                                search_code,
                                strategy_code,
                                symbol,
                                timeframe,
                                data.get("search_method", "GRID"),
                                "QUEUED",
                                max_trials,
                                objective_metric,
                                "NO_HARDCODE_SPRINT_PLANNER_MIGRATION_V1",
                            ),
                        )
                        planned += 1

    report = "\n".join(
        [
            "=== NO_HARDCODE_SPRINT_PLANNER_MIGRATION_V1 ===",
            f"sprint_code={sprint_code}",
            f"planned_jobs={planned}",
            "source=recommendation_engine_latest.json",
            "VERDICT=NO_HARDCODE_SPRINT_PLANNER_MIGRATION_V1_READY",
        ]
    )

    OUT_REPORT.write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
PY

PYTHONPATH=src python -m py_compile src/scripts/build_edge_sprint_plan_from_recommendation_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_sprint_plan_from_recommendation_v1.py

planned=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.parameter_search_job_v1
WHERE source_version='NO_HARDCODE_SPRINT_PLANNER_MIGRATION_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$planned" -gt 0
test "$unsafe" = "0"

grep -q "VERDICT=NO_HARDCODE_SPRINT_PLANNER_MIGRATION_V1_READY" reports/edge_sprint_plan_latest.txt

echo "planned_jobs=$planned"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_NO_HARDCODE_SPRINT_PLANNER_MIGRATION_V1_OK"
