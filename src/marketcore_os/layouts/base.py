from __future__ import annotations

import os
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

APP_VERSION = "0.1.4"

MENU_ITEMS = [
    ("workspace", "Рабочее место", "Workspace"),
    ("capital", "Капитал", "Capital"),
    ("edge", "Edge", "Edge"),
    ("research", "Исследования", "Research"),
    ("intraday", "Интрадей", "Intraday"),
    ("portfolio", "Портфель", "Portfolio"),
    ("risk", "Риск", "Risk"),
    ("program", "Программа", "Program"),
    ("settings", "Настройки", "Settings"),
]


def normalize_lang(lang: str | None) -> str:
    return "en" if lang == "en" else "ru"


def normalize_theme(theme: str | None) -> str:
    return "dark" if theme == "dark" else "light"


def tr(lang: str, ru: str, en: str) -> str:
    return en if normalize_lang(lang) == "en" else ru


def current_time_for_tz(tz: str) -> str:
    try:
        return datetime.now(ZoneInfo(tz)).strftime("%d.%m.%Y %H:%M:%S")
    except Exception:
        return datetime.now(ZoneInfo("UTC")).strftime("%d.%m.%Y %H:%M:%S UTC")


def tz_label(tz: str) -> str:
    return {
        "Europe/Moscow": "MSK",
        "UTC": "UTC",
        "Europe/London": "London",
        "America/New_York": "New York",
        "Asia/Tokyo": "Tokyo",
    }.get(tz, tz)


def render_shell(*, content: str, lang: str, tz: str, currency: str, theme: str) -> str:
    lang = normalize_lang(lang)
    theme = normalize_theme(theme)
    current_time = current_time_for_tz(tz)
    build = os.getenv("MARKETCORE_BUILD", "dev")[:8]

    menu = "".join(
        f'<a href="/{"" if key == "workspace" else key}">{escape(tr(lang, ru, en))}</a>'
        for key, ru, en in MENU_ITEMS
    )

    return f"""<!doctype html>
<html lang="{escape(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MarketCore OS</title>
<style>
:root {{
  --bg:#f6f7fb; --card:#ffffff; --text:#111827; --muted:#6b7280;
  --line:#e5e7eb; --accent:#111827;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  background:var(--bg); color:var(--text);
}}
body.mc-dark {{
  --bg:#0f172a; --card:#111827; --text:#f9fafb; --muted:#cbd5e1;
  --line:#334155; --accent:#f9fafb;
}}
.mc-header {{
  min-height:56px; display:flex; align-items:center; justify-content:space-between;
  gap:12px; padding:8px 16px; background:var(--card); border-bottom:1px solid var(--line);
  position:sticky; top:0; z-index:10;
}}
.mc-left {{ display:flex; align-items:center; gap:12px; min-width:0; }}
.mc-menu-button {{
  width:40px; height:40px; border:1px solid var(--line); border-radius:10px;
  background:var(--card); color:var(--text); font-size:22px; cursor:pointer;
}}
.mc-title {{ font-weight:700; white-space:nowrap; }}
.mc-status-bar {{ display:flex; gap:8px; align-items:center; justify-content:flex-end; flex-wrap:wrap; }}
.mc-pill {{
  border:1px solid var(--line); border-radius:999px; padding:6px 10px;
  background:var(--card); color:var(--text); font-size:13px; white-space:nowrap;
}}
.mc-layout {{ display:grid; grid-template-columns:240px 1fr; min-height:calc(100vh - 56px); }}
.mc-nav {{ border-right:1px solid var(--line); background:var(--card); padding:14px; }}
.mc-nav a {{
  display:block; color:var(--text); text-decoration:none; padding:10px 12px;
  border-radius:10px; margin-bottom:4px;
}}
.mc-nav a:hover {{ background:rgba(148,163,184,0.16); }}
.mc-workspace {{ padding:18px; max-width:1280px; }}
.mc-workspace-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.mc-card {{
  background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px;
}}
.mc-card-wide {{ grid-column:1 / -1; }}
.mc-row {{
  display:flex; justify-content:space-between; align-items:center; gap:16px;
  padding:8px 0; border-bottom:1px solid rgba(148,163,184,0.20);
}}
.mc-row:last-child {{ border-bottom:0; }}
.mc-label {{ color:var(--muted); }}
.mc-value {{ font-weight:700; text-align:right; white-space:nowrap; }}
.mc-badge {{
  display:inline-block; border-radius:999px; padding:4px 9px; font-size:12px; font-weight:700;
}}
.mc-ok {{ background:#dcfce7; color:#166534; }}
.mc-info {{ background:#dbeafe; color:#1e40af; }}
.mc-off {{ background:#f3f4f6; color:#374151; }}
.mc-bad {{ background:#fee2e2; color:#991b1b; }}
.mc-next {{ border:2px solid var(--accent); }}
.mc-footer {{ padding:12px 18px; color:var(--muted); font-size:12px; }}
@media (max-width: 800px) {{
  .mc-layout {{ grid-template-columns:1fr; }}
  .mc-nav {{ display:none; }}
  .mc-workspace-grid {{ grid-template-columns:1fr; }}
  .mc-card-wide {{ grid-column:auto; }}
  .mc-workspace {{ padding:12px; }}
  .mc-status-bar {{ justify-content:flex-start; }}
}}
</style>
</head>
<body class="mc-{escape(theme)}">
<header class="mc-header">
  <div class="mc-left">
    <button class="mc-menu-button" aria-label="{escape(tr(lang, "меню", "menu"))}">☰</button>
    <div class="mc-title">MarketCore OS</div>
  </div>
  <div class="mc-status-bar">
    <span class="mc-pill">🟢 ONLINE</span>
    <span class="mc-pill">{escape(lang.upper())}</span>
    <span class="mc-pill">{escape(tz_label(tz))}</span>
    <span class="mc-pill">{escape(current_time)}</span>
    <span class="mc-pill">{escape(currency)}</span>
    <span class="mc-pill">PostgreSQL ✓</span>
    <span class="mc-pill">Build {escape(build)}</span>
  </div>
</header>
<div class="mc-layout">
  <nav class="mc-nav">{menu}</nav>
  <main class="mc-workspace">{content}</main>
</div>
<footer class="mc-footer">MarketCore OS {APP_VERSION} · read-only</footer>
</body>
</html>"""
