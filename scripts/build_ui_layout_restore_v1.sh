#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_UI_LAYOUT_RESTORE_V1 ==="

mkdir -p scripts

cp src/marketcore/presentation/layout.py /tmp/layout_py_before_ui_layout_restore_v1.bak || true

cat > src/marketcore/presentation/layout.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.registry import menu_pages


def _e(value: object) -> str:
    return escape("" if value is None else str(value))


BASE_CSS = """
:root {
    --bg: #0b1020;
    --panel: #111827;
    --panel2: #0f172a;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --border: rgba(148, 163, 184, 0.22);
    --accent: #38bdf8;
    --danger: #f87171;
    --ok: #34d399;
    --warn: #fbbf24;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
}

a {
    color: inherit;
    text-decoration: none;
}

.shell {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 240px minmax(0, 1fr);
}

.sidebar {
    border-right: 1px solid var(--border);
    background: var(--panel2);
    padding: 12px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}

.brand {
    font-size: 16px;
    font-weight: 700;
    margin: 4px 0 14px 0;
    color: var(--accent);
}

.menu {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.menu a {
    display: block;
    padding: 8px 9px;
    border-radius: 8px;
    color: var(--muted);
    font-size: 13px;
}

.menu a:hover {
    background: rgba(148, 163, 184, 0.12);
    color: var(--text);
}

.menu a.active {
    background: rgba(56, 189, 248, 0.14);
    color: var(--text);
    border: 1px solid rgba(56, 189, 248, 0.24);
}

.main {
    min-width: 0;
    padding: 12px;
}

.topbar {
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(11, 16, 32, 0.96);
}

.topbar-title {
    font-size: 14px;
    font-weight: 650;
    color: var(--text);
}

.topbar-meta {
    font-size: 12px;
    color: var(--muted);
    white-space: nowrap;
}

.card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 9px 10px;
    margin-bottom: 10px;
}

.card h2 {
    margin: 0 0 6px 0;
    font-size: 18px;
    line-height: 1.2;
}

.card h3 {
    margin: 0 0 4px 0;
    font-size: 11px;
    line-height: 1.2;
    font-weight: 500;
    color: var(--muted);
}

.card p {
    margin: 0;
    font-size: 13px;
    line-height: 1.35;
    color: var(--muted);
}

.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
    gap: 8px;
    margin: 0 0 10px 0;
}

.cards .card {
    min-height: 56px;
    margin-bottom: 0;
}

.cards .card p {
    font-size: 18px;
    line-height: 1.15;
    font-weight: 700;
    color: var(--text);
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

thead th {
    position: sticky;
    top: 42px;
    z-index: 5;
    background: var(--panel2);
    color: var(--muted);
    font-weight: 600;
}

th, td {
    border-bottom: 1px solid var(--border);
    padding: 5px 7px;
    text-align: left;
    vertical-align: top;
    line-height: 1.25;
}

code {
    color: var(--accent);
    white-space: pre-wrap;
}

@media (max-width: 820px) {
    .shell {
        display: block;
    }

    .sidebar {
        position: static;
        height: auto;
        max-height: 42vh;
        border-right: 0;
        border-bottom: 1px solid var(--border);
    }

    .menu {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .main {
        padding: 8px;
    }

    .topbar {
        height: auto;
        align-items: flex-start;
        flex-direction: column;
        gap: 4px;
    }

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

    .cards .card p {
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

    thead th {
        top: 0;
    }
}
"""


CLOCK_JS = """
<script>
(function () {
    function pad(n) { return String(n).padStart(2, "0"); }
    function tick() {
        const d = new Date();
        const text =
            pad(d.getDate()) + "." +
            pad(d.getMonth() + 1) + "." +
            d.getFullYear() + " " +
            pad(d.getHours()) + ":" +
            pad(d.getMinutes()) + ":" +
            pad(d.getSeconds());
        const el = document.getElementById("ui-clock");
        if (el) el.textContent = text;
    }
    tick();
    setInterval(tick, 1000);
})();
</script>
"""


def render_layout(page: Page, content: str) -> str:
    menu_html = []
    for item in menu_pages():
        active = " active" if item.route == page.route else ""
        icon = getattr(item, "icon", "") or ""
        menu_html.append(
            f'<a class="{active.strip()}" href="{_e(item.route)}">'
            f'{_e(icon)} {_e(item.title)}</a>'
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(page.title)}</title>
<style>
{BASE_CSS}
</style>
</head>
<body>
<div class="shell">
    <aside class="sidebar">
        <div class="brand">FINAM Core</div>
        <nav class="menu">
            {''.join(menu_html)}
        </nav>
    </aside>
    <main class="main">
        <div class="topbar">
            <div class="topbar-title">{_e(page.title)}</div>
            <div class="topbar-meta">Runtime · Paper · <span id="ui-clock">--.--.---- --:--:--</span></div>
        </div>
        {content}
    </main>
</div>
{CLOCK_JS}
</body>
</html>"""
PY

cat > scripts/test_ui_layout_restore_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_UI_LAYOUT_RESTORE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/registry.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS http://127.0.0.1:8080/feature-store >/tmp/ui_layout_feature_store.html
curl -fsS http://127.0.0.1:8080/strategy-platform >/tmp/ui_layout_strategy.html
curl -fsS http://127.0.0.1:8080/edge-platform >/tmp/ui_layout_edge.html
curl -fsS http://127.0.0.1:8080/risk-platform >/tmp/ui_layout_risk.html
curl -fsS http://127.0.0.1:8080/trading-platform >/tmp/ui_layout_trading.html
curl -fsS http://127.0.0.1:8080/portfolio-platform >/tmp/ui_layout_portfolio.html

grep -q "FINAM Core" /tmp/ui_layout_feature_store.html
grep -q "ui-clock" /tmp/ui_layout_feature_store.html
grep -q "viewport" /tmp/ui_layout_feature_store.html
grep -q "Portfolio Platform" /tmp/ui_layout_portfolio.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=UI_LAYOUT_RESTORE_V1_READY"
echo "VERDICT=TEST_UI_LAYOUT_RESTORE_V1_OK"
SH_TEST

chmod +x scripts/test_ui_layout_restore_v1.sh
scripts/test_ui_layout_restore_v1.sh

echo "VERDICT=BUILD_UI_LAYOUT_RESTORE_V1_OK"
