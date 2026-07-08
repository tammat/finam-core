#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_REPOSITORY_V1 ==="

file="src/marketcore/recommendation/repository.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_recommendation_repository \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -RInE \
'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' \
"$file"; then
    echo "DANGEROUS_CODE_FOUND"
    exit 1
fi

if grep -RInE \
"SBER|LKOH|VTBR|GAZP|BUY|SELL|LONG|SHORT|80|70|60|50|0\.70|0\.80|0\.90" \
"$file"; then
    echo "HARDCODE_FOUND_IN_REPOSITORY"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
import psycopg2

from marketcore.recommendation.evaluator import RecommendationEvaluator, RecommendationRule
from marketcore.recommendation.loader import RecommendationContextLoader
from marketcore.recommendation.parameter_loader import PlatformParameterLoader
from marketcore.recommendation.repository import RecommendationRepository

contexts = RecommendationContextLoader().load()
params = PlatformParameterLoader().load()

if not contexts:
    print("repository_smoke=NO_CONTEXT")
    raise SystemExit(0)

with psycopg2.connect("postgresql:///finam_core") as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT rule_code, recommendation_code, priority
            FROM knowledge.recommendation_rule_v1
            WHERE enabled
            ORDER BY priority
        """)
        rule_rows = cur.fetchall()

        rules = []
        for rule_code, recommendation_code, priority in rule_rows:
            cur.execute("""
                SELECT metric_code, operator_code, parameter_code
                FROM knowledge.recommendation_rule_condition_v1
                WHERE rule_code=%s
                  AND enabled
                ORDER BY condition_order
            """, (rule_code,))
            conditions = [
                {
                    "metric_code": r[0],
                    "operator_code": r[1],
                    "parameter_code": r[2],
                }
                for r in cur.fetchall()
            ]
            rules.append(
                RecommendationRule(
                    rule_code=rule_code,
                    recommendation_code=recommendation_code,
                    priority=int(priority),
                    conditions=conditions,
                )
            )

result = RecommendationEvaluator().evaluate(contexts[0], rules, params)
recommendation_id = RecommendationRepository().save(result)

assert recommendation_id > 0

with psycopg2.connect("postgresql:///finam_core") as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM knowledge.recommendation_reason_v1
            WHERE recommendation_id=%s
            """,
            (recommendation_id,),
        )
        reason_rows = cur.fetchone()[0]

assert reason_rows >= 1

print("recommendation_repository=OK")
print("recommendation_id=", recommendation_id)
print("reason_rows=", reason_rows)
PY

result_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_result_v1
WHERE source_version='MARKET_CONTEXT_RECOMMENDATION_REPOSITORY_V1';
")

reason_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_reason_v1
WHERE source_version='MARKET_CONTEXT_RECOMMENDATION_REPOSITORY_V1';
")

test "$result_rows" -ge 1
test "$reason_rows" -ge 1

echo "recommendation_result_rows=$result_rows"
echo "recommendation_reason_rows=$reason_rows"
echo "repository_business_logic=0"
echo "hardcode=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_REPOSITORY_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_REPOSITORY_V1_OK"
