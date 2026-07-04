#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MULTI_STRATEGY_ENGINE_SCHEMA_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/006_strategy_signal_snapshot_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.strategy_signal_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,

    symbol TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    signal_ts TIMESTAMPTZ NOT NULL,

    signal_direction TEXT NOT NULL DEFAULT 'FLAT',
    signal_strength NUMERIC(20,6) NOT NULL DEFAULT 0,
    signal_score NUMERIC(20,6) NOT NULL DEFAULT 0,
    confidence NUMERIC(20,6) NOT NULL DEFAULT 0,
    signal_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    feature_quality_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    market_quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    paper_allowed BOOLEAN NOT NULL DEFAULT false,
    risk_allowed BOOLEAN NOT NULL DEFAULT false,
    execution_allowed BOOLEAN NOT NULL DEFAULT false,

    feature_version TEXT NOT NULL DEFAULT 'FEATURE_STORE_V1',
    strategy_version TEXT NOT NULL DEFAULT 'MULTI_STRATEGY_ENGINE_SCHEMA_V1',
    source_table TEXT NOT NULL DEFAULT 'analytics.feature_snapshot_v1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_strategy_signal_snapshot_v1
        UNIQUE (symbol, timeframe, strategy_family, signal_ts)
);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_symbol_tf_ts
ON analytics.strategy_signal_snapshot_v1(symbol, timeframe, signal_ts DESC);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_strategy
ON analytics.strategy_signal_snapshot_v1(strategy_family);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_score
ON analytics.strategy_signal_snapshot_v1(signal_score DESC);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_status
ON analytics.strategy_signal_snapshot_v1(signal_status);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat > src/scripts/build_strategy_signal_snapshot_schema_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT to_regclass('analytics.strategy_signal_snapshot_v1') AS reg;")
            reg = cur.fetchone()["reg"]

            if reg != "analytics.strategy_signal_snapshot_v1":
                raise RuntimeError("analytics.strategy_signal_snapshot_v1 not found")

    print("=== MULTI_STRATEGY_ENGINE_SCHEMA_V1 ===")
    print("schema_ready=1")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MULTI_STRATEGY_ENGINE_SCHEMA_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_multi_strategy_engine_schema_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_STRATEGY_ENGINE_SCHEMA_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/006_strategy_signal_snapshot_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_strategy_signal_snapshot_schema_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_signal_snapshot_schema_v1.py \
  | tee /tmp/multi_strategy_engine_schema_v1.txt

grep -q "VERDICT=MULTI_STRATEGY_ENGINE_SCHEMA_V1_READY" \
  /tmp/multi_strategy_engine_schema_v1.txt

exists=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.strategy_signal_snapshot_v1') IS NOT NULL;")
test "$exists" = "t"

psql -d finam_core -c "\d analytics.strategy_signal_snapshot_v1"

echo "table_exists=$exists"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MULTI_STRATEGY_ENGINE_SCHEMA_V1_OK"
SH_TEST

chmod +x scripts/test_multi_strategy_engine_schema_v1.sh
scripts/test_multi_strategy_engine_schema_v1.sh

echo "VERDICT=BUILD_MULTI_STRATEGY_ENGINE_SCHEMA_V1_OK"
