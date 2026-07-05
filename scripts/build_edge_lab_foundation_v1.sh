#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_LAB_FOUNDATION_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/015_edge_lab_foundation_v1.sql <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS analytics.edge_lab_run_v1 (
    id BIGSERIAL PRIMARY KEY,
    run_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    research_batch_id TEXT NOT NULL DEFAULT 'DEFAULT',
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL DEFAULT 'default',
    parameter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dataset_version TEXT NOT NULL DEFAULT 'default',
    runner_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    status_code TEXT NOT NULL DEFAULT 'QUEUED',
    source_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(research_code, strategy_code, symbol, timeframe, parameter_hash, dataset_version)
);

CREATE TABLE IF NOT EXISTS analytics.edge_observation_v1 (
    id BIGSERIAL PRIMARY KEY,
    observation_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    run_uuid UUID NOT NULL,
    research_batch_id TEXT NOT NULL DEFAULT 'DEFAULT',
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL DEFAULT 'default',
    parameter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dataset_version TEXT NOT NULL DEFAULT 'default',
    market_data_version TEXT NOT NULL DEFAULT 'default',
    runner_version TEXT NOT NULL DEFAULT 'unknown',
    score_formula_version TEXT NOT NULL DEFAULT 'unknown',
    market_regime TEXT NOT NULL DEFAULT 'UNKNOWN',
    bars_used INTEGER NOT NULL DEFAULT 0,
    trades INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    win_rate NUMERIC(12,6) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(12,6) NOT NULL DEFAULT 0,
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_win NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_loss NUMERIC(20,8) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(20,8) NOT NULL DEFAULT 0,
    recovery_factor NUMERIC(12,6) NOT NULL DEFAULT 0,
    sharpe NUMERIC(12,6) NOT NULL DEFAULT 0,
    sortino NUMERIC(12,6) NOT NULL DEFAULT 0,
    ulcer_index NUMERIC(12,6) NOT NULL DEFAULT 0,
    commission NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage NUMERIC(20,8) NOT NULL DEFAULT 0,
    stability_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    raw_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    normalized_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    research_cost_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    research_cpu_ms BIGINT NOT NULL DEFAULT 0,
    research_memory_mb NUMERIC(12,4) NOT NULL DEFAULT 0,
    research_elapsed_ms BIGINT NOT NULL DEFAULT 0,
    verdict_code TEXT NOT NULL DEFAULT 'OBSERVED',
    source_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_uuid)
);

CREATE TABLE IF NOT EXISTS analytics.edge_candidate_v1 (
    id BIGSERIAL PRIMARY KEY,
    candidate_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    observation_uuid UUID NOT NULL,
    research_batch_id TEXT NOT NULL DEFAULT 'DEFAULT',
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL DEFAULT 'default',
    parameter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dataset_version TEXT NOT NULL DEFAULT 'default',
    raw_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    normalized_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    stability_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    candidate_status TEXT NOT NULL DEFAULT 'EDGE_CANDIDATE',
    validation_stage TEXT NOT NULL DEFAULT 'NOT_STARTED',
    paper_allowed BOOLEAN NOT NULL DEFAULT false,
    shadow_allowed BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
    live_allowed BOOLEAN NOT NULL DEFAULT false,
    approved_at TIMESTAMPTZ,
    source_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(observation_uuid)
);

CREATE INDEX IF NOT EXISTS ix_edge_lab_run_v1_status ON analytics.edge_lab_run_v1(status_code);
CREATE INDEX IF NOT EXISTS ix_edge_lab_run_v1_research_code ON analytics.edge_lab_run_v1(research_code);
CREATE INDEX IF NOT EXISTS ix_edge_observation_v1_strategy_symbol ON analytics.edge_observation_v1(strategy_code, symbol, timeframe);
CREATE INDEX IF NOT EXISTS ix_edge_observation_v1_verdict ON analytics.edge_observation_v1(verdict_code);
CREATE INDEX IF NOT EXISTS ix_edge_candidate_v1_status ON analytics.edge_candidate_v1(candidate_status);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_lab_run_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_observation_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_candidate_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat > src/scripts/build_edge_lab_foundation_v1.py <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BATCH_ID = os.getenv("RESEARCH_BATCH_ID", datetime.utcnow().strftime("%Y%m%d_EDGE_LAB_BOOTSTRAP"))


def parameter_hash(parameter_set: object) -> str:
    raw = json.dumps(parameter_set or {}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def main() -> None:
    created = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    research_code,
                    strategy_code,
                    symbol,
                    timeframe,
                    parameter_set
                FROM analytics.research_queue_v1
                WHERE status_code='QUEUED'
                ORDER BY priority ASC, id ASC;
            """)
            rows = cur.fetchall()

            for r in rows:
                params = r["parameter_set"] or {}
                ph = parameter_hash(params)

                cur.execute("""
                    INSERT INTO analytics.edge_lab_run_v1 (
                        research_batch_id,
                        research_code,
                        strategy_code,
                        strategy_version,
                        symbol,
                        timeframe,
                        parameter_hash,
                        parameter_json,
                        dataset_version,
                        runner_version,
                        status_code,
                        source_version,
                        updated_at
                    )
                    VALUES (
                        %s,%s,%s,'v1',%s,%s,%s,%s::jsonb,
                        'default',
                        'EDGE_LAB_FOUNDATION_V1',
                        'QUEUED',
                        'EDGE_LAB_FOUNDATION_V1',
                        now()
                    )
                    ON CONFLICT(research_code, strategy_code, symbol, timeframe, parameter_hash, dataset_version)
                    DO UPDATE SET
                        research_batch_id=EXCLUDED.research_batch_id,
                        parameter_json=EXCLUDED.parameter_json,
                        runner_version=EXCLUDED.runner_version,
                        status_code='QUEUED',
                        source_version='EDGE_LAB_FOUNDATION_V1',
                        updated_at=now();
                """, (
                    BATCH_ID,
                    r["research_code"],
                    r["strategy_code"],
                    r["symbol"],
                    r["timeframe"],
                    ph,
                    json.dumps(params, ensure_ascii=False, sort_keys=True),
                ))
                created += 1

            cur.execute("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE status_code='QUEUED') AS queued,
                    count(*) FILTER (WHERE status_code='RUNNING') AS running,
                    count(*) FILTER (WHERE status_code='DONE') AS done,
                    count(*) FILTER (WHERE status_code='FAILED') AS failed
                FROM analytics.edge_lab_run_v1;
            """)
            summary = cur.fetchone()

    print("=== EDGE_LAB_FOUNDATION_V1 ===")
    print(f"research_batch_id={BATCH_ID}")
    print(f"runs_generated={created}")
    print(f"runs_total={summary['total']}")
    print(f"queued={summary['queued']}")
    print(f"running={summary['running']}")
    print(f"done={summary['done']}")
    print(f"failed={summary['failed']}")
    print("observations_created=0")
    print("candidates_created=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_LAB_FOUNDATION_V1_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.lab.title": "Edge Lab",
        "edge.lab.subtitle": "Лаборатория оценки исследовательских наблюдений и кандидатов edge.",
        "edge.lab.run": "Запуск исследования",
        "edge.lab.runs": "Запуски исследований",
        "edge.lab.observation": "Наблюдение",
        "edge.lab.observations": "Наблюдения",
        "edge.lab.candidate": "Edge-кандидат",
        "edge.lab.candidates": "Edge-кандидаты",
        "edge.lab.score": "Edge Score",
        "edge.lab.raw_score": "Raw Edge Score",
        "edge.lab.normalized_score": "Normalized Edge Score",
        "edge.lab.confidence": "Confidence",
        "edge.lab.stability": "Stability",
        "edge.lab.status": "Статус",
        "edge.lab.verdict": "Вердикт",
        "edge.lab.research_cost": "Research Cost",
        "edge.lab.batch": "Research Batch",
        "edge.lab.parameter_hash": "Parameter Hash",
        "edge.lab.dataset_version": "Dataset Version",
        "edge.lab.runner_version": "Runner Version",
        "edge.lab.score_formula_version": "Score Formula",
        "edge.status.QUEUED": "В очереди",
        "edge.status.RUNNING": "В работе",
        "edge.status.DONE": "Завершено",
        "edge.status.FAILED": "Ошибка",
        "edge.verdict.OBSERVED": "Наблюдение",
        "edge.verdict.REJECT": "Отклонить",
        "edge.verdict.CANDIDATE": "Кандидат",
        "edge.candidate.status.EDGE_CANDIDATE": "Edge-кандидат",
        "edge.candidate.status.VALIDATION": "Валидация",
        "edge.candidate.status.PAPER": "Paper",
        "edge.candidate.status.SHADOW": "Shadow",
        "edge.candidate.status.MICRO_LIVE": "Micro Live",
        "edge.validation.stage.NOT_STARTED": "Не начато",
        "edge.validation.stage.IN_PROGRESS": "В работе",
        "edge.validation.stage.PASSED": "Пройдено",
        "edge.validation.stage.FAILED": "Не пройдено"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_lab_foundation_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_LAB_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/015_edge_lab_foundation_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_lab_foundation_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_lab_foundation_v1.py | tee /tmp/edge_lab_foundation_v1.txt

grep -q "VERDICT=EDGE_LAB_FOUNDATION_V1_READY" /tmp/edge_lab_foundation_v1.txt

run_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1;")
queued_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='QUEUED';")
observation_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.edge_observation_v1') IS NOT NULL;")
candidate_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.edge_candidate_v1') IS NOT NULL;")

test "$run_rows" -gt 0
test "$queued_rows" -gt 0
test "$observation_table" = "t"
test "$candidate_table" = "t"

grep -q "edge.lab.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.candidate.status.EDGE_CANDIDATE" src/marketcore/presentation/ui_labels.py
grep -q "edge.validation.stage.NOT_STARTED" src/marketcore/presentation/ui_labels.py

echo "edge_lab_run_rows=$run_rows"
echo "edge_lab_queued_rows=$queued_rows"
echo "edge_observation_table=$observation_table"
echo "edge_candidate_table=$candidate_table"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_LAB_FOUNDATION_V1_OK"
SH_TEST

chmod +x scripts/test_edge_lab_foundation_v1.sh
scripts/test_edge_lab_foundation_v1.sh

echo "VERDICT=BUILD_EDGE_LAB_FOUNDATION_V1_OK"
