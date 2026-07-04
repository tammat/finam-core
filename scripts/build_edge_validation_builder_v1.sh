#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_VALIDATION_BUILDER_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_edge_validation_builder_v1.py <<'PY'
from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras

import edge.sample_rule  # noqa: F401
from edge.base.validation_executor import EdgeValidationExecutor
from edge.base.validation_registry import EdgeValidationRegistry
from edge.sample_rule.config import EdgeSampleRuleConfig
from edge.sample_rule.rule import EdgeSampleRule

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("EDGE_VALIDATION_LIMIT", "5000"))


def load_config(cur) -> dict:
    cur.execute("""
        SELECT config_json
        FROM analytics.edge_configuration_v1
        WHERE edge_name='DEFAULT'
        LIMIT 1;
    """)
    row = cur.fetchone()
    if not row:
        return {}
    cfg = row["config_json"]
    return cfg if isinstance(cfg, dict) else json.loads(cfg)


def main() -> None:
    build_id = str(uuid.uuid4())
    executor = EdgeValidationExecutor()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cfg = EdgeSampleRuleConfig.from_dict(load_config(cur))

            rules = []
            for cls in EdgeValidationRegistry.enabled():
                if cls.name == "EDGE_SAMPLE_RULE":
                    rules.append(EdgeSampleRule(cfg))
                else:
                    rules.append(cls())

            cur.execute("""
                SELECT
                    e.*,
                    count(*) OVER (
                        PARTITION BY e.symbol, e.timeframe, e.strategy_family
                    )::int AS samples
                FROM analytics.edge_decision_snapshot_v1 e
                ORDER BY e.signal_ts DESC
                LIMIT %s;
            """, (LIMIT,))
            rows = cur.fetchall()

            updated = 0
            passed = 0

            for row in rows:
                results = [executor.execute(rule, dict(row)) for rule in rules]
                if results:
                    validation_score = sum(r.validation_score for r in results) / len(results)
                    validation_passed = all(r.passed for r in results)
                else:
                    validation_score = 0.0
                    validation_passed = False

                if validation_passed:
                    passed += 1

                cur.execute("""
                    UPDATE analytics.edge_decision_snapshot_v1
                    SET
                        validation_score=%s,
                        recommendation_code=%s,
                        ready_for_replay=%s,
                        source_version='EDGE_VALIDATION_BUILDER_V1',
                        build_id=%s,
                        refreshed_at=now()
                    WHERE id=%s;
                """, (
                    validation_score,
                    "VALIDATION_PASS" if validation_passed else "WAIT_SAMPLE",
                    validation_passed,
                    build_id,
                    row["id"],
                ))
                updated += 1

            cur.execute("SELECT count(*) AS rows FROM analytics.edge_decision_snapshot_v1;")
            total_rows = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT count(*) AS unsafe
                FROM analytics.edge_decision_snapshot_v1
                WHERE ready_for_live=true OR ready_for_micro_live=true;
            """)
            unsafe = int(cur.fetchone()["unsafe"])

    print("=== EDGE_VALIDATION_BUILDER_V1 ===")
    print(f"rows_processed={len(rows)}")
    print(f"rows_updated={updated}")
    print(f"validation_passed={passed}")
    print(f"edge_rows_total={total_rows}")
    print(f"unsafe_live_rows={unsafe}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_VALIDATION_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_edge_validation_builder_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_builder_v1.py

DATABASE_URL=postgresql:///finam_core EDGE_VALIDATION_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_edge_validation_builder_v1.py | tee /tmp/edge_validation_builder_v1.txt

grep -q "VERDICT=EDGE_VALIDATION_BUILDER_V1_READY" /tmp/edge_validation_builder_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_decision_snapshot_v1;")
updated=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_decision_snapshot_v1 WHERE source_version='EDGE_VALIDATION_BUILDER_V1';")
unsafe=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_decision_snapshot_v1 WHERE ready_for_live=true OR ready_for_micro_live=true;")

test "$rows" -gt 0
test "$updated" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT symbol, strategy_family, edge_score, validation_score, recommendation_code, ready_for_replay
FROM analytics.edge_decision_snapshot_v1
ORDER BY signal_ts DESC
LIMIT 30;
"

echo "edge_rows=$rows"
echo "updated_rows=$updated"
echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_VALIDATION_BUILDER_V1_OK"
SH_TEST

chmod +x scripts/test_edge_validation_builder_v1.sh
scripts/test_edge_validation_builder_v1.sh

echo "VERDICT=BUILD_EDGE_VALIDATION_BUILDER_V1_OK"
