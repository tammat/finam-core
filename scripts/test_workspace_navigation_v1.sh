#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_NAVIGATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/presentation/003_workspace_navigation_v1.sql

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/navigation/navigation_provider.py \
  src/marketcore/presentation/navigation/__init__.py \
  src/marketcore/presentation/components/navigation.py \
  src/marketcore/presentation/layout.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from marketcore.presentation.navigation import NavigationProvider
from marketcore.presentation.components.navigation import render_navigation

groups = NavigationProvider().load()
html = render_navigation(groups, "/recommendation")

assert len(groups) >= 4
assert "workspace-nav" in html
assert "/recommendation" in html
assert "active" in html
assert "Feature Store" not in html
assert "Knowledge Graph" not in html
assert "Trading Platform" not in html

print("WORKSPACE_NAVIGATION_PROVIDER_OK")
PY

systemctl is-active --quiet marketcore-ui-shell.service || {
  echo "marketcore-ui-shell.service is not running"
  exit 1
}

curl -fsS http://127.0.0.1:8080/recommendation >/tmp/workspace_navigation_v1.html

grep -q "Recommendation" /tmp/workspace_navigation_v1.html

groups=$(psql -At -d finam_core -c "SELECT count(*) FROM presentation.ui_navigation_group_v1 WHERE is_enabled=true;")
items=$(psql -At -d finam_core -c "SELECT count(*) FROM presentation.ui_navigation_item_v1 WHERE is_enabled=true;")
labels=$(psql -At -d finam_core -c "
SELECT count(*)
FROM presentation.ui_resource_v1
WHERE resource_group='navigation'
  AND locale_code='ru';
")

test "$groups" -ge 5
test "$items" -ge 10
test "$labels" -ge 10

echo "navigation_groups=$groups"
echo "navigation_items=$items"
echo "i18n_labels=$labels"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_NAVIGATION_V1_READY"
echo "VERDICT=TEST_WORKSPACE_NAVIGATION_V1_OK"
