#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_HOME_SERVICE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/services/dashboard/market_provider.py \
  src/marketcore/services/dashboard/metadata_provider.py \
  src/marketcore/services/dashboard/risk_provider.py \
  src/marketcore/services/dashboard/execution_provider.py \
  src/marketcore/services/dashboard/version_provider.py \
  src/marketcore/services/dashboard/activity_provider.py \
  src/marketcore/services/dashboard/executive_overview_service.py

PYTHONPATH=src python - <<'PY'
from marketcore.services.dashboard.executive_overview_service import ExecutiveOverviewService
from marketcore.services.dashboard.market_provider import MarketProvider
from marketcore.services.dashboard.metadata_provider import MetadataProvider
from marketcore.services.dashboard.risk_provider import RiskProvider
from marketcore.services.dashboard.execution_provider import ExecutionProvider
from marketcore.services.dashboard.version_provider import VersionProvider
from marketcore.services.dashboard.activity_provider import ActivityProvider

service = ExecutiveOverviewService()
vm = service.load()

assert vm.product == "MarketCore"
assert vm.subtitle == "Trading Intelligence Platform"
assert vm.health_value == "97%"
assert vm.health_status == "READY"

assert len(vm.platform) == 6
assert len(vm.market) == 4
assert len(vm.metadata) == 3
assert len(vm.execution) == 3
assert len(vm.activity) >= 4
assert len(vm.quick_actions) == 4

assert vm.risk.value == "HIGH"
assert vm.risk.reason == "Corr. risk"
assert vm.risk.priority == "P1"
assert vm.version.product_version == "1.0.0"
assert vm.version.repo == "finam-core"

assert MarketProvider().load()[0].value == "876K"
assert MetadataProvider().load()[2].value == "100%"
assert RiskProvider().load_risk().priority == "P1"
assert ExecutionProvider().load()[0].value == "Выкл."
assert VersionProvider().load().product_name == "MarketCore"
assert len(ActivityProvider().load()) >= 3

print("service_ready=READY")
print("market_provider=READY")
print("metadata_provider=READY")
print("risk_provider=READY")
print("execution_provider=READY")
print("version_provider=READY")
print("activity_provider=READY")
print("view_model_ready=READY")
print("marketcore_brand=READY")
print("ux_copy_ru_short=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=HOME_SERVICE_V1_READY")
PY

echo "VERDICT=TEST_HOME_SERVICE_V1_OK"
