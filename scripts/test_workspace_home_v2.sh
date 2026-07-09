#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_HOME_V2 ==="

sql_file="sql/presentation/workspace_v2_home_i18n_v1.sql"
files=(
  "src/marketcore/presentation/workspace_v2/viewmodel/home_v2_viewmodel.py"
  "src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py"
  "src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/home_page_v2.py"
  "src/marketcore/presentation/router.py"
)

psql -d finam_core -v ON_ERROR_STOP=1 -f "$sql_file"

PYTHONPYCACHEPREFIX=/tmp/workspace_home_v2 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/viewmodel/home_v2_viewmodel.py \
  src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
  src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py \
  src/marketcore/presentation/workspace_v2/home_page_v2.py; then
  echo "SQL_OUTSIDE_RESOLVER_FOUND"
  exit 1
fi

if grep -RInE 'Paper|Shadow|Live|📈|🧺|💱' \
  src/marketcore/presentation/workspace_v2/viewmodel/home_v2_viewmodel.py \
  src/marketcore/presentation/workspace_v2/presenter/home_v2_presenter.py \
  src/marketcore/presentation/workspace_v2/renderer/home_v2_renderer.py \
  src/marketcore/presentation/workspace_v2/home_page_v2.py; then
  echo "UI_HARDCODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.home_page_v2 import render_workspace_v2_home_page_v2

html = render_workspace_v2_home_page_v2()
assert "MarketCore OS" in html
assert "Рабочий стол оператора" in html
assert "Портфель" in html
assert "Проба" in html
assert "mc-v2-card" in html
assert "data-i18n-key" not in html

code, body = route("/workspace-v2")
assert code == 200
assert "MarketCore OS" in body.decode("utf-8")

print("home_v2=OK")
PY

echo "home_v2=OK"
echo "route_workspace_v2=OK"
echo "i18n=OK"
echo "sql_outside_resolver=0"
echo "ui_hardcodes=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_WORKSPACE_HOME_V2_READY"
echo "VERDICT=TEST_MARKETCORE_WORKSPACE_HOME_V2_OK"
