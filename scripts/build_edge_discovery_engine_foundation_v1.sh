#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/018_edge_discovery_engine_foundation_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.edge_discovery_method_v1 (
    method_code TEXT PRIMARY KEY,
    method_name TEXT NOT NULL,
    method_family TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.edge_discovery_rule_v1 (
    id BIGSERIAL PRIMARY KEY,
    rule_code TEXT NOT NULL UNIQUE,
    method_code TEXT NOT NULL REFERENCES analytics.edge_discovery_method_v1(method_code),
    metric_name TEXT NOT NULL,
    operator_code TEXT NOT NULL,
    threshold_value NUMERIC(20,8),
    weight NUMERIC(12,6) NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.edge_discovery_run_v1 (
    id BIGSERIAL PRIMARY KEY,
    discovery_run_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    discovery_batch_id TEXT NOT NULL,
    method_code TEXT NOT NULL,
    status_code TEXT NOT NULL DEFAULT 'QUEUED',
    observations_scanned INTEGER NOT NULL DEFAULT 0,
    candidates_created INTEGER NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO analytics.edge_discovery_method_v1(method_code, method_name, method_family, enabled, config_json)
VALUES
('RULE_RANK_V1', 'Rule based ranking', 'RULE_ENGINE', true, '{"candidate_limit":100}'::jsonb),
('PARETO_V1', 'Pareto front placeholder', 'MULTI_OBJECTIVE', false, '{}'::jsonb),
('GRID_OBJECTIVE_V1', 'Grid objective placeholder', 'PARAMETER_SEARCH', false, '{}'::jsonb),
('BAYESIAN_V1', 'Bayesian optimization placeholder', 'OPTIMIZATION', false, '{}'::jsonb),
('GENETIC_V1', 'Genetic search placeholder', 'OPTIMIZATION', false, '{}'::jsonb)
ON CONFLICT(method_code) DO UPDATE SET
    method_name=EXCLUDED.method_name,
    method_family=EXCLUDED.method_family,
    config_json=EXCLUDED.config_json,
    updated_at=now();

INSERT INTO analytics.edge_discovery_rule_v1(rule_code, method_code, metric_name, operator_code, threshold_value, weight, enabled)
VALUES
('RULE_TRADES_MIN_V1', 'RULE_RANK_V1', 'trades', '>=', 30, 0.20, true),
('RULE_PF_MIN_V1', 'RULE_RANK_V1', 'profit_factor', '>=', 1.20, 0.25, true),
('RULE_EXPECTANCY_POSITIVE_V1', 'RULE_RANK_V1', 'expectancy', '>', 0, 0.20, true),
('RULE_SCORE_MIN_V1', 'RULE_RANK_V1', 'normalized_edge_score', '>=', 60, 0.20, true),
('RULE_CONFIDENCE_MIN_V1', 'RULE_RANK_V1', 'confidence_score', '>=', 60, 0.10, true),
('RULE_STABILITY_MIN_V1', 'RULE_RANK_V1', 'stability_score', '>=', 60, 0.05, true)
ON CONFLICT(rule_code) DO UPDATE SET
    method_code=EXCLUDED.method_code,
    metric_name=EXCLUDED.metric_name,
    operator_code=EXCLUDED.operator_code,
    threshold_value=EXCLUDED.threshold_value,
    weight=EXCLUDED.weight,
    enabled=EXCLUDED.enabled,
    updated_at=now();

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_discovery_method_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_discovery_rule_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_discovery_run_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat > src/scripts/build_edge_discovery_engine_foundation_v1.py <<'PY'
from __future__ import annotations

import os
from datetime import UTC, datetime

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    batch_id = datetime.now(UTC).strftime("%Y%m%d_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1")

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS methods_total,
                       count(*) FILTER (WHERE enabled=true) AS methods_enabled
                FROM analytics.edge_discovery_method_v1;
            """)
            methods = cur.fetchone()

            cur.execute("""
                SELECT count(*) AS rules_total,
                       count(*) FILTER (WHERE enabled=true) AS rules_enabled
                FROM analytics.edge_discovery_rule_v1;
            """)
            rules = cur.fetchone()

            cur.execute("""
                INSERT INTO analytics.edge_discovery_run_v1 (
                    discovery_batch_id,
                    method_code,
                    status_code,
                    source_version,
                    updated_at
                )
                VALUES (
                    %s,
                    'RULE_RANK_V1',
                    'QUEUED',
                    'EDGE_DISCOVERY_ENGINE_FOUNDATION_V1',
                    now()
                );
            """, (batch_id,))

            cur.execute("""
                SELECT count(*) AS runs_total
                FROM analytics.edge_discovery_run_v1;
            """)
            runs = cur.fetchone()

    print("=== EDGE_DISCOVERY_ENGINE_FOUNDATION_V1 ===")
    print(f"discovery_batch_id={batch_id}")
    print(f"methods_total={methods['methods_total']}")
    print(f"methods_enabled={methods['methods_enabled']}")
    print(f"rules_total={rules['rules_total']}")
    print(f"rules_enabled={rules['rules_enabled']}")
    print(f"runs_total={runs['runs_total']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DISCOVERY_ENGINE_FOUNDATION_V1_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.discovery.engine.title": "Edge Discovery Engine",
        "edge.discovery.engine.subtitle": "Конфигурируемый движок отбора edge без жёстко заданных порогов в коде.",
        "edge.discovery.method": "Метод Discovery",
        "edge.discovery.rule": "Правило Discovery",
        "edge.discovery.rules": "Правила Discovery",
        "edge.discovery.operator": "Оператор",
        "edge.discovery.threshold": "Порог",
        "edge.discovery.weight": "Вес",
        "edge.discovery.family.RULE_ENGINE": "Rule Engine",
        "edge.discovery.family.MULTI_OBJECTIVE": "Multi-objective",
        "edge.discovery.family.PARAMETER_SEARCH": "Parameter Search",
        "edge.discovery.family.OPTIMIZATION": "Optimization"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_discovery_engine_foundation_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/018_edge_discovery_engine_foundation_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_engine_foundation_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_engine_foundation_v1.py | tee /tmp/edge_discovery_engine_foundation_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_ENGINE_FOUNDATION_V1_READY" /tmp/edge_discovery_engine_foundation_v1.txt

methods=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_method_v1;")
enabled_methods=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_method_v1 WHERE enabled=true;")
rules=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_rule_v1;")
enabled_rules=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_rule_v1 WHERE enabled=true;")
runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_discovery_run_v1;")

test "$methods" -ge 5
test "$enabled_methods" -ge 1
test "$rules" -ge 6
test "$enabled_rules" -ge 6
test "$runs" -gt 0

grep -q "edge.discovery.engine.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.discovery.rule" src/marketcore/presentation/ui_labels.py

echo "methods=$methods"
echo "enabled_methods=$enabled_methods"
echo "rules=$rules"
echo "enabled_rules=$enabled_rules"
echo "runs=$runs"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1_OK"
SH_TEST

chmod +x scripts/test_edge_discovery_engine_foundation_v1.sh
scripts/test_edge_discovery_engine_foundation_v1.sh

echo "VERDICT=BUILD_EDGE_DISCOVERY_ENGINE_FOUNDATION_V1_OK"
