from __future__ import annotations

from marketcore.presentation.i18n.runtime import tr, translate

from marketcore.presentation.components.layout.sidebar import render_sidebar

from marketcore.presentation.components.layout.status_bar import render_status_bar
from marketcore.presentation.navigation import NavigationProvider
from marketcore.presentation.components.navigation import render_navigation

from html import escape

from marketcore.presentation.page import Page


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


def render_layout(page: Page | None = None, content: str = "", title: str | None = None, active_route: str | None = None) -> str:
    if page is not None:
        page_title = page.title
        route = page.route
    else:
        page_title = title or "MarketCore"
        route = active_route or "/"
    sidebar_html = render_sidebar(route)
    localized_page_title = translate(page_title)

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(localized_page_title)}</title>
<style>
{BASE_CSS}
</style>
</head>
<body>
<div class="shell">
    {sidebar_html}
    <main class="main">
        <div class="topbar">
            <div class="topbar-title">{_e(localized_page_title)}</div>
            <div class="topbar-meta">Read-only · MarketCore · <span id="ui-clock">--.--.---- --:--:--</span></div>
        </div>
        {content}
    </main>
</div>
{CLOCK_JS}
{render_status_bar()}
</body>
</html>"""
