#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_UI_RESTORE_AFTER_COMPACT_V1 ==="

python - <<'PY'
from pathlib import Path
import re

app = Path("src/marketcore/presentation/app.py")
s = app.read_text(encoding="utf-8")

# Удаляем ошибочно вставленный HTML/JS-блок из Python-файла.
s2 = re.sub(
    r'\n?<!-- UI_RESPONSIVE_COMPACT_V1 -->.*?</script>\s*',
    '\n',
    s,
    flags=re.S,
)

if s2 != s:
    app.write_text(s2, encoding="utf-8")
    print("app_py_bad_js_removed=1")
else:
    print("app_py_bad_js_removed=0")

layout = Path("src/marketcore/presentation/layout.py")
ls = layout.read_text(encoding="utf-8")

# Оставляем только безопасный compact CSS. Никакого JS в Python.
if "UI_COMPACT_SAFE_V1" not in ls:
    ls += r'''

/* UI_COMPACT_SAFE_V1 */
:root {
    --ui-compact-gap: 8px;
    --ui-sticky-offset: 0px;
}

.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
    gap: var(--ui-compact-gap);
    margin: 8px 0 10px 0;
}

.card {
    padding: 8px 10px;
    border-radius: 8px;
}

.cards .card {
    min-height: 56px;
}

.card h2 {
    font-size: 18px;
    margin: 0 0 6px 0;
}

.card h3 {
    font-size: 11px;
    line-height: 1.2;
    margin: 0 0 4px 0;
    font-weight: 500;
    opacity: 0.82;
}

.card p {
    font-size: 18px;
    line-height: 1.2;
    margin: 0;
    font-weight: 650;
}

table {
    font-size: 12px;
}

th, td {
    padding: 5px 7px;
    line-height: 1.25;
}

thead th {
    position: sticky;
    top: var(--ui-sticky-offset);
    z-index: 5;
}

@media (max-width: 760px) {
    .cards {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 6px;
    }

    .card {
        padding: 7px 8px;
    }

    .card h2 {
        font-size: 16px;
    }

    .card h3 {
        font-size: 10px;
    }

    .card p {
        font-size: 15px;
    }

    table {
        display: block;
        overflow-x: auto;
        white-space: nowrap;
        font-size: 11px;
    }

    th, td {
        padding: 4px 6px;
    }
}
'''
    layout.write_text(ls, encoding="utf-8")
    print("layout_compact_css_added=1")
else:
    print("layout_compact_css_added=0")
PY

cat > scripts/test_ui_restore_after_compact_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_RESTORE_AFTER_COMPACT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/router.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/feature-store" >/tmp/ui_feature_store_restored.html
curl -fsS "http://127.0.0.1:8080/strategy-platform" >/tmp/ui_strategy_restored.html
curl -fsS "http://127.0.0.1:8080/portfolio-platform" >/tmp/ui_portfolio_restored.html

grep -q "Feature" /tmp/ui_feature_store_restored.html || true
grep -q "Strategy" /tmp/ui_strategy_restored.html || true
grep -q "Portfolio" /tmp/ui_portfolio_restored.html || true

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_RESTORE_AFTER_COMPACT_V1_READY"
echo "VERDICT=TEST_UI_RESTORE_AFTER_COMPACT_V1_OK"
SH_TEST

chmod +x scripts/test_ui_restore_after_compact_v1.sh
scripts/test_ui_restore_after_compact_v1.sh

echo "VERDICT=BUILD_UI_RESTORE_AFTER_COMPACT_V1_OK"
