from __future__ import annotations

from html import escape

from marketcore.presentation.navigation import render_navigation
from marketcore.presentation.ui_labels import display_label
from marketcore.presentation.ui_text import normalize_ui_text


def render_layout(title: str, active_route: str, content: str) -> bytes:
    page_title = normalize_ui_text(display_label(active_route, title))
    content = normalize_ui_text(content)

    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{escape(page_title)}</title>
<style>
:root {{
  --bg:#0f172a;
  --sidebar:#111827;
  --card:#111827;
  --card2:#0b1220;
  --text:#e5e7eb;
  --muted:#94a3b8;
  --line:#374151;
  --accent:#93c5fd;
  --accent2:#bfdbfe;
  --ok:#22c55e;
  --warn:#f59e0b;
  --bad:#ef4444;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
}}
.app {{
  display:grid;
  grid-template-columns:280px 1fr;
  min-height:100vh;
}}
.sidebar {{
  background:var(--sidebar);
  border-right:1px solid var(--line);
  padding:18px;
  position:sticky;
  top:0;
  height:100vh;
  overflow:auto;
}}
.logo {{
  font-size:20px;
  font-weight:800;
  margin-bottom:6px;
}}
.subtitle {{
  color:var(--muted);
  font-size:13px;
  margin-bottom:18px;
}}
.nav-item {{
  display:flex;
  align-items:center;
  gap:10px;
  padding:10px 12px;
  color:#cbd5e1;
  text-decoration:none;
  border-radius:10px;
  margin-bottom:6px;
  border:1px solid transparent;
}}
.nav-item.active,
.nav-item:hover {{
  background:#1f2937;
  color:#fff;
  border-color:#334155;
}}
.nav-icon {{
  width:22px;
  display:inline-block;
  text-align:center;
  color:var(--accent2);
}}
.main {{
  padding:24px;
  max-width:1600px;
}}
.header {{
  margin-bottom:18px;
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:16px;
}}
.header h1 {{
  margin:0;
  font-size:28px;
}}
.shell-badge {{
  color:var(--muted);
  font-size:13px;
  border:1px solid var(--line);
  border-radius:999px;
  padding:6px 10px;
}}
.card {{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:14px;
  padding:18px;
  margin-bottom:14px;
}}
.card h2 {{
  margin-top:0;
}}
.card p {{
  color:#cbd5e1;
}}
a {{
  color:var(--accent);
}}
table {{
  border-collapse:collapse;
  width:100%;
  margin-top:12px;
}}
th,td {{
  border-bottom:1px solid var(--line);
  padding:8px;
  text-align:left;
  font-size:14px;
  vertical-align:top;
}}
th {{
  color:var(--accent2);
  font-weight:700;
}}
.badge {{
  display:inline-block;
  padding:3px 8px;
  border-radius:999px;
  background:#1f2937;
  color:var(--accent2);
}}
.footer {{
  margin-top:24px;
  color:var(--muted);
  font-size:13px;
}}
@media (max-width: 900px) {{
  .app {{
    grid-template-columns:1fr;
  }}
  .sidebar {{
    position:relative;
    height:auto;
  }}
}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div class="logo">MarketCore OS</div>
<div class="subtitle">Единая оболочка платформы</div>
<nav>{render_navigation(active_route)}</nav>
</aside>
<main class="main">
<header class="header">
  <h1>{escape(page_title)}</h1>
  <div class="shell-badge">MARKETCORE_UI_SHELL_V1 · RU · MSK · RUB</div>
</header>
{content}
<footer class="footer">MARKETCORE_UI_SHELL_V1</footer>
</main>
</div>
</body>
</html>"""
    return html.encode("utf-8")
