#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1 ==="

files=(
src/marketcore/recommendation/execution_context_models.py
src/marketcore/recommendation/execution_context_repository.py
)

for f in "${files[@]}"
do
    test -f "$f"

    PYTHONPYCACHEPREFIX=/tmp/finam_pycache_exec_models \
    PYTHONPATH=src \
    python -m py_compile "$f"
done

if grep -RInE \
'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|DROP TABLE|TRUNCATE' \
"${files[@]}"
then
    echo DANGEROUS_CODE_FOUND
    exit 1
fi

if grep -RInE \
'SBER|LKOH|GAZP|VTBR|BUY|SELL|LONG|SHORT' \
"${files[@]}"
then
    echo HARDCODE_FOUND
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from marketcore.recommendation.execution_context_models import RecommendationExecutionContext

ctx = RecommendationExecutionContext(
    recommendation_id=1,
    direction_code="DIRECTION_UP",
    entry_price=Decimal("100"),
    invalidation_price=Decimal("95"),
    target_price=Decimal("110"),
    stop_loss_price=Decimal("95"),
    take_profit_price=Decimal("110"),
    trailing_enabled=False,
    trailing_step=Decimal("0"),
    trailing_activation_price=Decimal("0"),
    horizon_bars=20,
    risk_unit=Decimal("1"),
    source_context_id=1,
    source_edge_context_id=1,
    evidence={}
)

assert ctx.recommendation_id == 1
assert ctx.direction_code == "DIRECTION_UP"

print("execution_context_model=OK")
PY

echo "repository_mode=insert_only"
echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1_READY"
echo "VERDICT=TEST_RECOMMENDATION_EXECUTION_CONTEXT_MODELS_V1_OK"
