from __future__ import annotations

from html import escape

from marketcore.presentation.navigation import render_navigation


def render_layout(title: str, active_route: str, content: str) -> bytes:
    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
body {{ margin:0; font-family:system-ui,-apple-system,sans-serif; background:#0f172a; color:#e5e7eb; }}
.app {{ display:grid; grid-template-columns:260px 1fr; min-height:100vh; }}
.sidebar {{ background:#111827; border-right:1px solid #374151; padding:18px; }}
.logo {{ font-size:20px; font-weight:700; margin-bottom:20px; }}
.nav-item {{ display:block; padding:10px 12px; color:#cbd5e1; text-decoration:none; border-radius:10px; margin-bottom:6px; }}
.nav-item.active, .nav-item:hover {{ background:#1f2937; color:#fff; }}
.main {{ padding:24px; }}
.header {{ margin-bottom:18px; }}
.card {{ background:#111827; border:1px solid #374151; border-radius:14px; padding:18px; }}
.footer {{ margin-top:24px; color:#94a3b8; font-size:13px; }}
.badge {{ display:inline-block; padding:3px 8px; border-radius:999px; background:#1f2937; color:#bfdbfe; }}
table {{ border-collapse:collapse; width:100%; margin-top:12px; }}
th,td {{ border-bottom:1px solid #374151; padding:8px; text-align:left; font-size:14px; }}
th {{ color:#bfdbfe; }}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div class="logo">MarketCore OS</div>
<nav>{render_navigation(active_route)}</nav>
</aside>
<main class="main">
<header class="header"><h1>{escape(title)}</h1></header>
{content}
<footer class="footer">MARKETCORE_UI_SHELL_V1</footer>
</main>
</div>
</body>
</html>"""
    return html.encode("utf-8")
