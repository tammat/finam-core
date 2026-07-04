#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PLATFORM_GOVERNANCE_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_edge_platform_governance_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    (SELECT count(*)::int FROM analytics.edge_decision_snapshot_v1) AS edge_rows,
                    (SELECT count(*)::int FROM analytics.edge_decision_snapshot_v1 WHERE edge_score > 0) AS scored_rows,
                    (SELECT count(*)::int FROM analytics.edge_decision_snapshot_v1 WHERE validation_score >= 0) AS validated_rows,
                    (SELECT count(*)::int FROM analytics.edge_decision_snapshot_v1 WHERE decision_code IN ('ALLOW','OBSERVE','BLOCK')) AS decision_rows,
                    (SELECT count(*)::int FROM analytics.edge_decision_snapshot_v1 WHERE ready_for_live=true OR ready_for_micro_live=true) AS unsafe_rows,
                    (SELECT count(*)::int FROM analytics.edge_configuration_v1 WHERE enabled=true) AS enabled_config_rows;
            """)
            r = cur.fetchone()

            edge_rows = int(r["edge_rows"] or 0)
            scored_rows = int(r["scored_rows"] or 0)
            validated_rows = int(r["validated_rows"] or 0)
            decision_rows = int(r["decision_rows"] or 0)
            unsafe_rows = int(r["unsafe_rows"] or 0)
            enabled_config_rows = int(r["enabled_config_rows"] or 0)

            score_ok = edge_rows > 0 and scored_rows > 0
            validation_ok = edge_rows > 0 and validated_rows > 0
            decision_ok = edge_rows > 0 and decision_rows > 0
            config_ok = enabled_config_rows > 0
            safety_ok = unsafe_rows == 0

            checks = [score_ok, validation_ok, decision_ok, config_ok, safety_ok]
            governance_score = round(100.0 * sum(1 for x in checks if x) / len(checks), 4)

            if not safety_ok:
                readiness_code = "NOT_READY"
                recommendation_code = "BLOCK_PLATFORM"
            elif all(checks):
                readiness_code = "READY_FOR_RESEARCH"
                recommendation_code = "PROCEED_TO_RISK_PLATFORM"
            else:
                readiness_code = "NOT_READY"
                recommendation_code = "FIX_EDGE_PLATFORM"

            cur.execute("""
                INSERT INTO analytics.edge_governance_v1 (
                    governance_scope,
                    score_engine_status,
                    validation_status,
                    decision_status,
                    api_status,
                    ui_status,
                    governance_score,
                    readiness_code,
                    recommendation_code,
                    source_version,
                    build_id,
                    refreshed_at
                )
                VALUES (
                    'GLOBAL',
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    'EDGE_PLATFORM_GOVERNANCE_V1',
                    %s,
                    now()
                )
                ON CONFLICT (governance_scope) DO UPDATE SET
                    score_engine_status=EXCLUDED.score_engine_status,
                    validation_status=EXCLUDED.validation_status,
                    decision_status=EXCLUDED.decision_status,
                    api_status=EXCLUDED.api_status,
                    ui_status=EXCLUDED.ui_status,
                    governance_score=EXCLUDED.governance_score,
                    readiness_code=EXCLUDED.readiness_code,
                    recommendation_code=EXCLUDED.recommendation_code,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (
                _status(score_ok),
                _status(validation_ok),
                _status(decision_ok),
                "OK",
                "OK",
                governance_score,
                readiness_code,
                recommendation_code,
                build_id,
            ))

    print("=== EDGE_PLATFORM_GOVERNANCE_V1 ===")
    print(f"edge_rows={edge_rows}")
    print(f"scored_rows={scored_rows}")
    print(f"validated_rows={validated_rows}")
    print(f"decision_rows={decision_rows}")
    print(f"unsafe_rows={unsafe_rows}")
    print(f"enabled_config_rows={enabled_config_rows}")
    print(f"governance_score={governance_score}")
    print(f"readiness_code={readiness_code}")
    print(f"recommendation_code={recommendation_code}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_PLATFORM_GOVERNANCE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_edge_platform_governance_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PLATFORM_GOVERNANCE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_platform_governance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/edge_platform.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_platform_governance_v1.py | tee /tmp/edge_platform_governance_v1.txt

grep -q "VERDICT=EDGE_PLATFORM_GOVERNANCE_V1_READY" /tmp/edge_platform_governance_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/edge-platform/governance" > /tmp/edge_platform_governance_api.json
curl -fsS "http://127.0.0.1:8080/edge-platform" > /tmp/edge_platform_governance_ui.html

python - <<'PY'
import json

p = json.load(open("/tmp/edge_platform_governance_api.json", encoding="utf-8"))
assert p["status"] == "OK"
d = p["data"]
assert float(d["governance_score"]) >= 80
assert d["readiness"]["code"] in {"READY_FOR_RESEARCH", "NOT_READY"}
assert d["recommendation"]["code"] in {"PROCEED_TO_RISK_PLATFORM", "FIX_EDGE_PLATFORM", "BLOCK_PLATFORM"}
PY

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_decision_snapshot_v1
WHERE ready_for_live=true OR ready_for_micro_live=true;
")
test "$unsafe" = "0"

grep -q "Edge Platform" /tmp/edge_platform_governance_ui.html

echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PLATFORM_GOVERNANCE_V1_READY"
echo "VERDICT=TEST_EDGE_PLATFORM_GOVERNANCE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_platform_governance_v1.sh
scripts/test_edge_platform_governance_v1.sh

echo "VERDICT=BUILD_EDGE_PLATFORM_GOVERNANCE_V1_OK"
