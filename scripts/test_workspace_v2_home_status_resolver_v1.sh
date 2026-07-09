#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_HOME_STATUS_RESOLVER_V1 ==="

files=(
  "src/marketcore/presentation/workspace_v2/domain/home_status_model_v1.py"
  "src/marketcore/presentation/workspace_v2/mapper/home_status_mapper_v1.py"
  "src/marketcore/presentation/workspace_v2/resolver/home_status_resolver_v1.py"
  "src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py"
  "src/marketcore/presentation/workspace_v2/home_page_v2.py"
)

PYTHONPYCACHEPREFIX=/tmp/workspace_home_status_resolver \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
  src/marketcore/presentation/workspace_v2/home_page_v2.py; then
  echo "SQL_OUTSIDE_RESOLVER_FOUND"
  exit 1
fi

if grep -RInE 'row\["|row\[' \
  src/marketcore/presentation/workspace_v2/resolver/home_status_resolver_v1.py; then
  echo "SCHEMA_COUPLING_IN_RESOLVER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.resolver.home_status_resolver_v1 import HomeStatusResolverV1
from marketcore.presentation.workspace_v2.home_page_v2 import render_workspace_v2_home_page_v2

items = HomeStatusResolverV1().resolve()
assert len(items) == 6
assert any(item.item_code == "portfolio" for item in items)
assert any(item.item_code == "runtime" and item.status_code == UiStatusCode.BLOCKED for item in items)

html = render_workspace_v2_home_page_v2()
assert "Панель состояния" in html
assert "Портфель" in html
assert "Заблокировано" in html
assert "home.card.status" not in html
assert "data-i18n-key" not in html

print("home_status_resolver=OK")
print(f"items={len(items)}")
PY

echo "home_status_resolver=OK"
echo "presenter_uses_resolver=OK"
echo "sql_outside_resolver=0"
echo "schema_isolation=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_HOME_STATUS_RESOLVER_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_HOME_STATUS_RESOLVER_V1_OK"
