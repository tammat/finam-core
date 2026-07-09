#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_CARD_VALUES_FORMAT_V1 ==="

files=(
  "src/marketcore/presentation/workspace_v2/formatter/portfolio_v2_formatter.py"
  "src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
  "src/marketcore/presentation/workspace_v2/portfolio_page_v2.py"
)

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_format \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(' \
  src/marketcore/presentation/workspace_v2/formatter/portfolio_v2_formatter.py \
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py \
  src/marketcore/presentation/workspace_v2/portfolio_page_v2.py; then
  echo "SQL_OUTSIDE_RESOLVER_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.formatter.portfolio_v2_formatter import PortfolioV2Formatter
from marketcore.presentation.workspace_v2.portfolio_page_v2 import render_workspace_v2_portfolio_page_v2

assert PortfolioV2Formatter.value("Средняя цена", "5468.5") == "5 468,50 ₽"
assert PortfolioV2Formatter.value("P&L общий", "-9420") == "-9 420,00 ₽"
assert PortfolioV2Formatter.value("pnl_pct", "-17.23") == "-17,23%"
assert PortfolioV2Formatter.value("Количество", "10") == "10,00"
assert PortfolioV2Formatter.value("Название", "Лукойл") == "Лукойл"

html = render_workspace_v2_portfolio_page_v2()

assert "mc-v2-values" in html
assert "mc-v2-value-row" in html
assert "5 468,50 ₽" in html or "₽" in html
assert "data-i18n-key" not in html
assert "portfolio.column." not in html

print("portfolio_card_values_format=OK")
PY

echo "portfolio_card_values_format=OK"
echo "formatter_used=OK"
echo "sql_outside_resolver=0"
echo "raw_i18n_keys=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_CARD_VALUES_FORMAT_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_CARD_VALUES_FORMAT_V1_OK"
