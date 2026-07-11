#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_KPI_API_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/profit_factory_kpi_api_pycache_v1 PYTHONPATH=src \
  .venv/bin/python -m py_compile \
  src/marketcore/services/profit_factory_kpi_service_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

result=$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from marketcore.services.profit_factory_kpi_service_v1 import ProfitFactoryKpiServiceV1

service = ProfitFactoryKpiServiceV1()
real = service.summary()
test = service.summary(scope="TEST")
candidates = service.candidates(scope="TEST")

invalid_rejected = 0
try:
    service.summary(scope="INVALID")
except ValueError:
    invalid_rejected = 1

print(real["data_scope"])
print(real["eligible_candidates"])
print(test["data_scope"])
print(test["eligible_candidates"])
print(len(candidates))
print(all(row["financial_kpi_eligible"] for row in candidates))
print(invalid_rejected)
PY
)

expected=$(printf 'REAL\n0\nTEST\n1\n1\nTrue\n1')
test "$result" = "$expected"

grep -q '"/api/kg/v1/profit-factory/kpi-summary"' \
  src/marketcore/api/serve_knowledge_graph_api_v1.py
grep -q '"/api/kg/v1/profit-factory/kpi-candidates"' \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

echo "$result"
echo "default_scope=REAL"
echo "invalid_scope_rejected=1"
echo "VERDICT=TEST_PROFIT_FACTORY_KPI_API_V1_OK"
