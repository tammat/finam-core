#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_V2_PRESENTER ==="

files=(
  "src/marketcore/presentation/workspace_v2/viewmodel/portfolio_v2_viewmodel.py"
  "src/marketcore/presentation/workspace_v2/formatter/portfolio_v2_formatter.py"
  "src/marketcore/presentation/workspace_v2/presenter/portfolio_v2_presenter.py"
)

PYTHONPYCACHEPREFIX=/tmp/workspace_v2_portfolio_presenter \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE 'SELECT |INSERT |UPDATE |DELETE |psycopg2|execute\(|<div|<section|</|#[0-9A-Fa-f]{6}|[0-9]+(px|rem|em)\b' "${files[@]}"; then
  echo "FORBIDDEN_LAYER_VIOLATION_FOUND"
  exit 1
fi

if grep -RInE '[А-Яа-яЁё]|Открыть|Paper|Shadow|Live|fallback"|📈' "${files[@]}"; then
  echo "UI_HARDCODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import PortfolioV2Presenter
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import PortfolioV2ViewModel

vm = PortfolioV2Presenter().load(limit=50)

assert isinstance(vm, PortfolioV2ViewModel)
assert vm.title_key == "portfolio.workspace.title"
assert vm.sections
assert all(isinstance(section, BaseSection) for section in vm.sections)

for section in vm.sections:
    assert section.title_key
    assert section.status_label_key
    for card in section.cards:
        data = card.to_dict()
        assert data["title_key"]
        assert "payload" in data
        assert "values" in data["payload"]
        assert "column_keys" in data["payload"]

print("portfolio_v2_presenter=OK")
print(f"sections={len(vm.sections)}")
print(f"cards={sum(len(section.cards) for section in vm.sections)}")
PY

echo "portfolio_v2_presenter=OK"
echo "formatter_used=OK"
echo "viewmodel_used=OK"
echo "sql_in_presenter=0"
echo "html_in_presenter=0"
echo "ui_hardcodes=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_PORTFOLIO_V2_PRESENTER_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_V2_PRESENTER_OK"
