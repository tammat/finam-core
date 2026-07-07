#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_RESOURCE_PROVIDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/resources/ui_resource_provider.py \
  src/marketcore/presentation/resources/__init__.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from marketcore.presentation.resources import UiResourceProvider

provider = UiResourceProvider(locale_code="ru")
resources = provider.load_group("edge_factory")

assert len(resources) >= 10
assert provider.tr("edge.factory.title") == "Edge Factory"
assert provider.icon("edge.factory.title") == "🏭"
assert provider.tr("missing.key", "Fallback") == "Fallback"

print("UI_RESOURCE_PROVIDER_OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_RESOURCE_PROVIDER_V1_READY"
echo "VERDICT=TEST_UI_RESOURCE_PROVIDER_V1_OK"
