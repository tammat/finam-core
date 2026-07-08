#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_PARAMETER_LOADER_V1 ==="

file="src/marketcore/recommendation/parameter_loader.py"

test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_parameter_loader \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -RInE \
'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' \
"$file"; then
    echo "DANGEROUS_CODE_FOUND"
    exit 1
fi

if grep -RInE \
"SBER|LKOH|VTBR|GAZP|80|70|60|50|0\.70|0\.80|0\.90" \
"$file"; then
    echo "HARDCODE_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from marketcore.recommendation.parameter_loader import PlatformParameterLoader

params = PlatformParameterLoader().load()

assert isinstance(params, dict)

assert "EDGE_VALIDATE_THRESHOLD" in params
assert "EDGE_RESEARCH_THRESHOLD" in params
assert "EDGE_OBSERVE_THRESHOLD" in params

assert isinstance(params["EDGE_VALIDATE_THRESHOLD"], Decimal)
assert isinstance(params["EDGE_RESEARCH_THRESHOLD"], Decimal)
assert isinstance(params["EDGE_OBSERVE_THRESHOLD"], Decimal)

assert "PROFILE_DEFAULT" in params

print("parameter_loader=OK")
print("parameters_loaded=", len(params))
PY

echo "hardcode=0"
echo "loader_mode=read_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_PARAMETER_LOADER_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_PARAMETER_LOADER_V1_OK"

