#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PIPELINE_V2_SCHEMA_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/001_edge_pipeline_snapshot_v1.sql <<'SQL'
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.edge_pipeline_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,

    symbol TEXT NOT NULL DEFAULT '',
    display_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    strategy_family TEXT NOT NULL DEFAULT '',

    pipeline_stage SMALLINT NOT NULL DEFAULT 10,
    overall_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    ranking_score NUMERIC(20,6) NOT NULL DEFAULT 0,
    research_priority TEXT NOT NULL DEFAULT 'UNKNOWN',
    research_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    validation_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    backtest_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    backtest_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    paper_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    paper_progress NUMERIC(10,2) NOT NULL DEFAULT 0,
    paper_trades INTEGER NOT NULL DEFAULT 0,

    risk_status TEXT NOT NULL DEFAULT 'NOT_READY',
    trading_status TEXT NOT NULL DEFAULT 'NOT_READY',
    runtime_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    source_version TEXT NOT NULL DEFAULT 'EDGE_PIPELINE_V2_SCHEMA_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_edge_pipeline_snapshot_v1_candidate
        UNIQUE (symbol, timeframe, strategy_family)
);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_symbol_tf
ON analytics.edge_pipeline_snapshot_v1(symbol, timeframe);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_stage
ON analytics.edge_pipeline_snapshot_v1(pipeline_stage);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_overall_status
ON analytics.edge_pipeline_snapshot_v1(overall_status);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_strategy_family
ON analytics.edge_pipeline_snapshot_v1(strategy_family);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_research_priority
ON analytics.edge_pipeline_snapshot_v1(research_priority);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;

ALTER DEFAULT PRIVILEGES IN SCHEMA analytics
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO alex;

ALTER DEFAULT PRIVILEGES IN SCHEMA analytics
GRANT USAGE, SELECT ON SEQUENCES TO alex;
SQL

cat > src/scripts/build_edge_pipeline_snapshot_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_PIPELINE_V2_SCHEMA_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT to_regclass('analytics.edge_pipeline_snapshot_v1') AS reg;")
            reg = cur.fetchone()["reg"]

            if reg != "analytics.edge_pipeline_snapshot_v1":
                raise RuntimeError("analytics.edge_pipeline_snapshot_v1 not found")

    print("=== EDGE_PIPELINE_SNAPSHOT_V1 ===")
    print(f"schema_ready=1")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_PIPELINE_V2_SCHEMA_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_edge_pipeline_v2_schema_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_SCHEMA_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/001_edge_pipeline_snapshot_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_pipeline_snapshot_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py \
  | tee /tmp/edge_pipeline_v2_schema_v1.txt

grep -q "VERDICT=EDGE_PIPELINE_V2_SCHEMA_V1_READY" \
  /tmp/edge_pipeline_v2_schema_v1.txt

psql -d finam_core -c "\d analytics.edge_pipeline_snapshot_v1"

table_exists=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.edge_pipeline_snapshot_v1') IS NOT NULL;")
test "$table_exists" = "t"

echo "table_exists=$table_exists"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_SCHEMA_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_SCHEMA_V1_OK"
SH_TEST

chmod +x scripts/test_edge_pipeline_v2_schema_v1.sh
scripts/test_edge_pipeline_v2_schema_v1.sh

echo "VERDICT=BUILD_EDGE_PIPELINE_V2_SCHEMA_V1_OK"
