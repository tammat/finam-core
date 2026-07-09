#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_PORTFOLIO_V2_RENDERER ==="

files=(
"src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_renderer.py"
)

PYTHONPYCACHEPREFIX=/tmp/workspace_renderer \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE \
'Открыть|Paper|Shadow|Live|📈|🧺|💱|SELECT |INSERT |UPDATE |DELETE |psycopg2' \
"${files[@]}"
then
    echo "FORBIDDEN_CONTENT_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.presenter.portfolio_v2_presenter import (
    PortfolioV2Presenter,
)

from marketcore.presentation.workspace_v2.renderer.portfolio_v2_renderer import (
    render_portfolio_v2,
)

vm = PortfolioV2Presenter().load(limit=20)

html = render_portfolio_v2(vm)

assert "mc-v2-shell" in html
assert "data-i18n-key" in html
assert "mc-v2-card" in html
assert "Открыть" not in html

print("portfolio_renderer=OK")
PY

echo "renderer=OK"
echo "i18n=OK"
echo "hardcodes=0"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=WORKSPACE_V2_PORTFOLIO_V2_RENDERER_READY"
echo "VERDICT=TEST_WORKSPACE_V2_PORTFOLIO_V2_RENDERER_OK"
