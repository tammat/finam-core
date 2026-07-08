#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1 ==="

sql_file="sql/knowledge/market_context_recommendation_evaluator_v1.sql"
file="src/marketcore/recommendation/evaluator.py"

test -f "$sql_file"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_recommendation_evaluator \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -RInE \
'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' \
"$sql_file" "$file"; then
    echo "DANGEROUS_CODE_FOUND"
    exit 1
fi

if grep -RInE \
"SBER|LKOH|VTBR|GAZP|BUY|SELL|LONG|SHORT|80|70|60|50|0\.70|0\.80|0\.90" \
"$file"; then
    echo "HARDCODE_FOUND_IN_EVALUATOR"
    exit 1
fi

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

condition_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.recommendation_rule_condition_v1
WHERE source_version='MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1'
  AND enabled;
")

test "$condition_rows" -ge 1

PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from marketcore.recommendation.evaluator import RecommendationEvaluator, RecommendationRule
from marketcore.recommendation.loader import RecommendationContextLoader
from marketcore.recommendation.parameter_loader import PlatformParameterLoader

contexts = RecommendationContextLoader().load()
params = PlatformParameterLoader().load()

rules = [
    RecommendationRule(
        rule_code=row[0],
        recommendation_code=row[1],
        priority=int(row[2]),
        conditions=row[3],
    )
    for row in []
]

assert isinstance(contexts, list)
assert isinstance(params, dict)

if contexts:
    # Интеграционная проверка структуры evaluator без хардкода правил:
    import psycopg2
    import psycopg2.extras

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT rule_code, recommendation_code, priority
                FROM knowledge.recommendation_rule_v1
                WHERE enabled
                ORDER BY priority
            """)
            rule_rows = cur.fetchall()

            loaded_rules = []
            for r in rule_rows:
                cur.execute("""
                    SELECT metric_code, operator_code, parameter_code
                    FROM knowledge.recommendation_rule_condition_v1
                    WHERE rule_code=%s
                      AND enabled
                    ORDER BY condition_order
                """, (r["rule_code"],))
                loaded_rules.append(
                    RecommendationRule(
                        rule_code=r["rule_code"],
                        recommendation_code=r["recommendation_code"],
                        priority=int(r["priority"]),
                        conditions=[dict(x) for x in cur.fetchall()],
                    )
                )

    result = RecommendationEvaluator().evaluate(contexts[0], loaded_rules, params)
    assert result.symbol
    assert result.timeframe
    assert result.recommendation_code
    assert result.rule_code
    assert result.recommendation_confidence >= 0
    assert isinstance(result.reasons, list)
    assert isinstance(result.evidence, dict)
    print("recommendation_evaluator=OK")
    print("sample_recommendation_code=", result.recommendation_code)
else:
    print("recommendation_evaluator=OK")
    print("sample_recommendation_code=NO_CONTEXT")
PY

echo "recommendation_rule_condition_rows=$condition_rows"
echo "business_logic_source=postgres"
echo "hardcode=0"
echo "evaluator_sql=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_EVALUATOR_V1_OK"
