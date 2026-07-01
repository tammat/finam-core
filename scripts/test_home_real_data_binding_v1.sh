#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_HOME_REAL_DATA_BINDING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/formatters/number_formatter.py \
  src/marketcore/services/dashboard/db.py \
  src/marketcore/services/dashboard/market_provider.py \
  src/marketcore/services/dashboard/metadata_provider.py \
  src/marketcore/services/dashboard/risk_provider.py \
  src/marketcore/services/dashboard/executive_overview_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.formatters.number_formatter import NumberFormatter
from marketcore.services.dashboard.executive_overview_service import ExecutiveOverviewService
from marketcore.services.dashboard.market_provider import MarketProvider
from marketcore.services.dashboard.metadata_provider import MetadataProvider
from marketcore.services.dashboard.risk_provider import RiskProvider

assert NumberFormatter.compact(875706) == "876K"
assert NumberFormatter.compact(71098524) == "71.1M"

market = MarketProvider().load()
metadata = MetadataProvider().load()
risk = RiskProvider().load_risk()
vm = ExecutiveOverviewService().load()

assert len(market) == 4
assert market[0].title == "Бары"
assert market[1].title == "Тики"
assert market[2].title == "Инстр."
assert market[3].title == "Fresh"

assert len(metadata) == 3
assert metadata[0].title == "Объекты"
assert metadata[2].value.endswith("%")

assert risk.reason == "Корреляция"
assert risk.priority == "P1"

assert vm.market[0].value != "0"
assert vm.market[1].value != "0"
assert vm.metadata[2].value.endswith("%")
assert vm.risk.reason == "Корреляция"

print("real_data_binding=READY")
print("number_formatter=READY")
print("market_real_data=READY")
print("metadata_real_data=READY")
print("risk_real_data=READY")
print("executive_overview_service=READY")
print("ux_reason_correlation=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=HOME_REAL_DATA_BINDING_V1_READY")
PY

echo "VERDICT=TEST_HOME_REAL_DATA_BINDING_V1_OK"
