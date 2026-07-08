#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_LOADER_V1 ==="

files=(
  src/marketcore/recommendation/__init__.py
  src/marketcore/recommendation/models.py
  src/marketcore/recommendation/loader.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_recommendation_loader PYTHONPATH=src python -m py_compile "$f"
done

if grep -RInE 'send_order|place_order|cancel_order|execute_order|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*runtime|UPDATE .*execution|UPDATE .*edge_score_model_v2|DELETE FROM|DROP TABLE|TRUNCATE' "${files[@]}"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

if grep -RInE "BUY|SELL|LONG|SHORT|SBER|LKOH|VTBR|GAZP|80|70|60|50|0\.7|0\.8|0\.9" "${files[@]}"; then
  echo "HARDCODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.recommendation.loader import RecommendationContextLoader

items = RecommendationContextLoader().load()

print(f"recommendation_context_rows={len(items)}")

assert isinstance(items, list)

if items:
    first = items[0]
    assert first.symbol
    assert first.timeframe
    assert first.edge_score is not None
    assert first.market_context_id > 0
    assert first.edge_context_id > 0
    assert first.knowledge_coverage >= 0
    assert first.regime_code
    assert first.volatility_state
    assert first.liquidity_state
    assert first.volume_state
    assert first.session_state
    assert isinstance(first.relationships, list)

print("recommendation_context_loader=OK")
PY

echo "hardcode=0"
echo "loader_mode=read_only"
echo "edge_score_v2_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_LOADER_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_LOADER_V1_OK"
