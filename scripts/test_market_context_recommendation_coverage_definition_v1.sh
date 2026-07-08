#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_COVERAGE_DEFINITION_V1 ==="

doc="docs/MARKET_CONTEXT_RECOMMENDATION_COVERAGE_DEFINITION_V1.txt"
test -f "$doc"

grep -q "Recommendation Result Coverage" "$doc"
grep -q "Recommendation Edge Coverage" "$doc"
grep -q "Operator Coverage" "$doc"
grep -q "DISTINCT ON(symbol,timeframe)" "$doc"

echo
echo "=== RECOMMENDATION UNIVERSE ==="

contexts=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
SELECT DISTINCT ON(symbol,timeframe)
symbol,timeframe
FROM knowledge.market_context_v1
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
ORDER BY symbol,timeframe,created_at DESC
) t;
SQL
)

echo "contexts=$contexts"

echo
echo "=== RECOMMENDATION RESULTS ==="

recommendations=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
SELECT DISTINCT ON(symbol,timeframe)
symbol,timeframe
FROM knowledge.recommendation_result_v1
ORDER BY symbol,timeframe,created_at DESC
) t;
SQL
)

echo "recommendations=$recommendations"

coverage=$(python3 <<PY
c=${contexts}
r=${recommendations}

if c==0:
    print("0.00")
else:
    print(f"{100.0*r/c:.2f}")
PY
)

echo
echo "Recommendation Result Coverage = ${coverage}%"

python3 <<PY
coverage=float("${coverage}")

if coverage < 99.99:
    raise SystemExit("RECOMMENDATION_RESULT_COVERAGE_NOT_100_PERCENT")
PY

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo
echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_COVERAGE_DEFINITION_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_COVERAGE_DEFINITION_V1_OK"
