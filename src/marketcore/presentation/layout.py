from __future__ import annotations

from html import escape

from marketcore.presentation.navigation import render_navigation
from marketcore.presentation.ui_labels import display_label

try:
    from marketcore.presentation.ui_text import normalize_ui_text
except Exception:
    def normalize_ui_text(text: str) -> str:
        return text


def render_layout(title: str, active_route: str, content: str) -> bytes:
    page_title = normalize_ui_text(display_label(active_route, title))
    normalized_content = normalize_ui_text(content)

    html = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>__PAGE_TITLE__</title>
<style>
:root {
  --bg:#0f172a;
  --sidebar:#111827;
  --card:#111827;
  --text:#e5e7eb;
  --muted:#94a3b8;
  --line:#374151;
  --accent:#93c5fd;
  --accent2:#bfdbfe;
}
* { box-sizing:border-box; }
body {
  margin:0;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
}
.app {
  display:grid;
  grid-template-columns:280px 1fr;
  min-height:100vh;
}
.sidebar {
  background:var(--sidebar);
  border-right:1px solid var(--line);
  padding:18px;
  position:sticky;
  top:0;
  height:100vh;
  overflow:auto;
}
.logo {
  font-size:20px;
  font-weight:800;
  margin-bottom:6px;
}
.subtitle {
  color:var(--muted);
  font-size:13px;
  margin-bottom:18px;
}
.nav-group {
  margin:14px 0 18px 0;
}
.nav-group-title {
  margin:14px 0 8px 0;
  padding:0 8px;
  color:#94a3b8;
  font-size:12px;
  font-weight:800;
  text-transform:uppercase;
  letter-spacing:.06em;
}
.nav-item {
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px 12px;
  color:#cbd5e1;
  text-decoration:none;
  border-radius:10px;
  margin-bottom:6px;
  border:1px solid transparent;
}
.nav-item.active,
.nav-item:hover {
  background:#1f2937;
  color:#fff;
  border-color:#334155;
}
.nav-icon {
  width:22px;
  display:inline-block;
  text-align:center;
  color:var(--accent2);
}
.main {
  padding:24px;
  max-width:1600px;
}
.header {
  margin-bottom:18px;
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
}
.header h1 {
  margin:0;
  font-size:28px;
}
.shell-badge {
  color:var(--muted);
  font-size:13px;
  border:1px solid var(--line);
  border-radius:999px;
  padding:6px 10px;
  white-space:nowrap;
}
.card {
  background:var(--card);
  border:1px solid var(--line);
  border-radius:14px;
  padding:18px;
  margin-bottom:14px;
}
.card h2 {
  margin-top:0;
}
.card p {
  color:#cbd5e1;
}
a {
  color:var(--accent);
}
table {
  border-collapse:collapse;
  width:100%;
  margin-top:12px;
}
th,td {
  border-bottom:1px solid var(--line);
  padding:8px;
  text-align:left;
  font-size:14px;
  vertical-align:top;
}
th {
  color:var(--accent2);
  font-weight:700;
}
.badge {
  display:inline-block;
  padding:3px 8px;
  border-radius:999px;
  background:#1f2937;
  color:var(--accent2);
}
.link-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:14px;
}
.link-card {
  display:block;
  background:#111827;
  border:1px solid #374151;
  border-radius:14px;
  padding:16px;
  text-decoration:none;
  color:#e5e7eb;
}
.link-card:hover {
  border-color:#93c5fd;
  background:#1f2937;
}
.link-card strong {
  display:block;
  margin-bottom:8px;
  color:#bfdbfe;
}
.link-card span {
  color:#cbd5e1;
  font-size:14px;
}
.footer {
  margin-top:24px;
  color:var(--muted);
  font-size:13px;
}
@media (max-width: 900px) {
  .app {
    grid-template-columns:1fr;
  }
  .sidebar {
    position:relative;
    height:auto;
  }
  .link-grid {
    grid-template-columns:1fr;
  }
}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div class="logo">MarketCore OS</div>
<div class="subtitle">Единая оболочка платформы</div>
<nav>__NAVIGATION__</nav>
</aside>
<main class="main">
<header class="header">
  <h1>__PAGE_TITLE__</h1>
  <div class="shell-badge">MARKETCORE_UI_SHELL_V1 · RU · MSK · RUB</div>
</header>
__CONTENT__
<footer class="footer">MARKETCORE_UI_SHELL_V1</footer>
</main>
</div>
</body>
</html>"""

    html = html.replace("__PAGE_TITLE__", escape(page_title))
    html = html.replace("__NAVIGATION__", render_navigation(active_route))
    html = html.replace("__CONTENT__", normalized_content)

    return html.encode("utf-8")
