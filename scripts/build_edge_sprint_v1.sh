#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_SPRINT_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/021_edge_sprint_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.edge_sprint_v1 (
    sprint_code TEXT PRIMARY KEY,
    sprint_name TEXT NOT NULL,
    status_code TEXT NOT NULL DEFAULT 'OPEN',
    objective_metric TEXT NOT NULL DEFAULT 'normalized_edge_score',
    target_observations INTEGER NOT NULL DEFAULT 1000,
    target_candidates INTEGER NOT NULL DEFAULT 10,
    notes TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'EDGE_SPRINT_V1',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.edge_sprint_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,
    sprint_code TEXT NOT NULL REFERENCES analytics.edge_sprint_v1(sprint_code),
    observations_total INTEGER NOT NULL DEFAULT 0,
    observations_with_trades INTEGER NOT NULL DEFAULT 0,
    candidates_total INTEGER NOT NULL DEFAULT 0,
    best_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    best_profit_factor NUMERIC(12,6) NOT NULL DEFAULT 0,
    best_expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    research_trades INTEGER NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'EDGE_SPRINT_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_sprint_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_sprint_snapshot_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat > src/scripts/build_edge_sprint_v1.py <<'PY'
from __future__ import annotations

import os
from datetime import UTC, datetime

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SPRINT_CODE = os.getenv("EDGE_SPRINT_CODE", datetime.now(UTC).strftime("EDGE_SPRINT_%Y%m%d"))
SPRINT_NAME = os.getenv("EDGE_SPRINT_NAME", "Edge Sprint V1")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.edge_sprint_v1 (
                    sprint_code, sprint_name, status_code, notes, updated_at
                )
                VALUES (%s,%s,'OPEN','Initial sprint for fast edge search',now())
                ON CONFLICT(sprint_code) DO UPDATE SET
                    sprint_name=EXCLUDED.sprint_name,
                    status_code='OPEN',
                    updated_at=now();
            """, (SPRINT_CODE, SPRINT_NAME))

            cur.execute("""
                SELECT
                    count(*) AS observations_total,
                    count(*) FILTER (WHERE trades > 0) AS observations_with_trades,
                    coalesce(max(normalized_edge_score), 0) AS best_score,
                    coalesce(max(profit_factor), 0) AS best_profit_factor,
                    coalesce(max(expectancy), 0) AS best_expectancy
                FROM analytics.edge_observation_v1;
            """)
            obs = cur.fetchone()

            cur.execute("SELECT count(*) AS c FROM analytics.edge_candidate_v1;")
            candidates = cur.fetchone()["c"]

            cur.execute("SELECT count(*) AS c FROM analytics.research_trade_v1;")
            trades = cur.fetchone()["c"]

            cur.execute("""
                INSERT INTO analytics.edge_sprint_snapshot_v1 (
                    sprint_code,
                    observations_total,
                    observations_with_trades,
                    candidates_total,
                    best_score,
                    best_profit_factor,
                    best_expectancy,
                    research_trades
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
            """, (
                SPRINT_CODE,
                obs["observations_total"],
                obs["observations_with_trades"],
                candidates,
                obs["best_score"],
                obs["best_profit_factor"],
                obs["best_expectancy"],
                trades,
            ))

    print("=== EDGE_SPRINT_V1 ===")
    print(f"sprint_code={SPRINT_CODE}")
    print(f"sprint_name={SPRINT_NAME}")
    print(f"observations_total={obs['observations_total']}")
    print(f"observations_with_trades={obs['observations_with_trades']}")
    print(f"candidates_total={candidates}")
    print(f"best_score={obs['best_score']}")
    print(f"best_profit_factor={obs['best_profit_factor']}")
    print(f"best_expectancy={obs['best_expectancy']}")
    print(f"research_trades={trades}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_SPRINT_V1_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.sprint.title": "Edge Sprint",
        "edge.sprint.subtitle": "Короткий исследовательский цикл поиска edge-кандидатов.",
        "edge.sprint.code": "Код спринта",
        "edge.sprint.observations": "Наблюдения",
        "edge.sprint.with_trades": "Наблюдения со сделками",
        "edge.sprint.candidates": "Кандидаты",
        "edge.sprint.best_score": "Лучший Score",
        "edge.sprint.best_profit_factor": "Лучший Profit Factor",
        "edge.sprint.best_expectancy": "Лучшая Expectancy"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_sprint_v1.sh <<'TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SPRINT_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/021_edge_sprint_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_sprint_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_sprint_v1.py | tee /tmp/edge_sprint_v1.txt

grep -q "VERDICT=EDGE_SPRINT_V1_READY" /tmp/edge_sprint_v1.txt

sprints=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_sprint_v1;")
snapshots=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_sprint_snapshot_v1;")

test "$sprints" -gt 0
test "$snapshots" -gt 0

grep -q "edge.sprint.title" src/marketcore/presentation/ui_labels.py

echo "sprints=$sprints"
echo "snapshots=$snapshots"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SPRINT_V1_OK"
TEST

chmod +x scripts/test_edge_sprint_v1.sh
scripts/test_edge_sprint_v1.sh

echo "VERDICT=BUILD_EDGE_SPRINT_V1_OK"
