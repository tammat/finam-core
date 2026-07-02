from __future__ import annotations

from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

APP_VERSION = "0.1.1"
DEFAULT_LANG = "ru"
DEFAULT_TZ = "Europe/Moscow"
DEFAULT_CURRENCY = "RUB"

app = FastAPI(title="MarketCore OS", version=APP_VERSION)


MENU_ITEMS = [
    ("home", "Главная", "Home"),
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


def tr(lang: str, ru: str, en: str) -> str:
    return en if normalize_lang(lang) == "en" else ru


def badge(text: str, kind: str = "ok") -> str:
    css = "mc-ok" if kind == "ok" else "mc-off"
    return f'<span class="mc-badge {css}">{escape(text)}</span>'


def row(label: str, value: str) -> str:
    return (
        '<div class="mc-row">'
        f'<span class="mc-label">{escape(label)}</span>'
        f'<span class="mc-value">{value}</span>'
        '</div>'
    )


def page_shell(content: str, lang: str, tz: str, currency: str) -> str:
    lang = normalize_lang(lang)
    menu = "".join(
        f'<a href="/#{escape(key)}">{escape(tr(lang, ru, en))}</a>'
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
  --bg:#f6f7fb;
  --card:#ffffff;
  --text:#111827;
  --muted:#6b7280;
  --line:#e5e7eb;
  --accent:#111827;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
}}
.mc-header {{
  height:56px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:0 16px;
  background:#fff;
  border-bottom:1px solid var(--line);
  position:sticky;
  top:0;
  z-index:10;
}}
.mc-left {{
  display:flex;
  align-items:center;
  gap:12px;
  min-width:0;
}}
.mc-menu-button {{
  width:40px;
  height:40px;
  border:1px solid var(--line);
  border-radius:10px;
  background:#fff;
  font-size:22px;
  cursor:pointer;
}}
.mc-title {{
  font-weight:700;
  white-space:nowrap;
}}
.mc-controls {{
  display:flex;
  gap:8px;
  align-items:center;
}}
.mc-pill {{
  border:1px solid var(--line);
  border-radius:999px;
  padding:6px 10px;
  background:#fff;
  font-size:13px;
}}
.mc-layout {{
  display:grid;
  grid-template-columns:240px 1fr;
  min-height:calc(100vh - 56px);
}}
.mc-nav {{
  border-right:1px solid var(--line);
  background:#fff;
  padding:14px;
}}
.mc-nav a {{
  display:block;
  color:var(--text);
  text-decoration:none;
  padding:10px 12px;
  border-radius:10px;
  margin-bottom:4px;
}}
.mc-nav a:hover {{ background:#f3f4f6; }}
.mc-workspace {{
  padding:18px;
  max-width:1200px;
}}
.mc-grid {{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:14px;
}}
.mc-card {{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:16px;
  padding:16px;
}}
.mc-row {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:16px;
  padding:8px 0;
  border-bottom:1px solid #f3f4f6;
}}
.mc-row:last-child {{ border-bottom:0; }}
.mc-label {{ color:var(--muted); }}
.mc-value {{
  font-weight:700;
  text-align:right;
  white-space:nowrap;
}}
.mc-badge {{
  display:inline-block;
  border-radius:999px;
  padding:4px 9px;
  font-size:12px;
  font-weight:700;
}}
.mc-ok {{ background:#dcfce7; color:#166534; }}
.mc-off {{ background:#f3f4f6; color:#374151; }}
.mc-next {{ border:2px solid var(--accent); }}
.mc-footer {{
  padding:12px 18px;
  color:var(--muted);
  font-size:12px;
}}
@media (max-width: 800px) {{
  .mc-layout {{ grid-template-columns:1fr; }}
  .mc-nav {{ display:none; }}
  .mc-grid {{ grid-template-columns:1fr; }}
  .mc-controls {{ gap:4px; }}
  .mc-pill {{ padding:5px 7px; font-size:12px; }}
  .mc-workspace {{ padding:12px; }}
}}
</style>
</head>
<body>
<header class="mc-header">
  <div class="mc-left">
    <button class="mc-menu-button" aria-label="{escape(tr(lang, "меню", "menu"))}">☰</button>
    <div class="mc-title">MarketCore OS</div>
  </div>
  <div class="mc-controls">
    <span class="mc-pill">{escape(lang.upper())}</span>
    <span class="mc-pill">{escape(tz)}</span>
    <span class="mc-pill">{escape(currency)}</span>
  </div>
</header>
<div class="mc-layout">
  <nav class="mc-nav">{menu}</nav>
  <main class="mc-workspace">{content}</main>
</div>
<footer class="mc-footer">MarketCore OS {APP_VERSION} · read-only</footer>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    lang = normalize_lang(request.query_params.get("lang", DEFAULT_LANG))
    tz = request.query_params.get("tz", DEFAULT_TZ)
    currency = request.query_params.get("currency", DEFAULT_CURRENCY)

    content = f"""
    <section class="mc-card">
      <h1>MarketCore OS</h1>
      <p>{escape(tr(lang, "Рабочее место управления капиталом", "Capital management workspace"))}</p>
    </section>

    <div class="mc-grid" style="margin-top:14px;">
      <section class="mc-card">
        <h3>{escape(tr(lang, "Капитал", "Capital"))}</h3>
        {row(tr(lang, "Плановый капитал", "Planned capital"), "500 000 ₽")}
        {row(tr(lang, "Работает", "Working"), "0%")}
        {row(tr(lang, "Свободно", "Available"), "100%")}
      </section>

      <section class="mc-card">
        <h3>{escape(tr(lang, "Двигатель прибыли", "Profit Engine"))}</h3>
        {row(tr(lang, "Research Candidate", "Research Candidate"), "54")}
        {row(tr(lang, "TOP3 Validation", "TOP3 Validation"), badge("COMPLETE"))}
        {row(tr(lang, "Paper Runtime", "Paper Runtime"), badge("READY"))}
      </section>

      <section class="mc-card">
        <h3>{escape(tr(lang, "Риск", "Risk"))}</h3>
        {row("Runtime", badge("OFF", "off"))}
        {row("Execution", badge("OFF", "off"))}
        {row("Micro Live", badge("OFF", "off"))}
      </section>

      <section class="mc-card mc-next">
        <h3>{escape(tr(lang, "Следующее действие", "Next Action"))}</h3>
        {row(tr(lang, "Действие", "Action"), "TOP3_PAPER_RUNTIME_EXECUTION_V1")}
        {row(tr(lang, "Статус", "Status"), badge("READY"))}
      </section>
    </div>
    """
    return HTMLResponse(page_shell(content, lang, tz, currency))


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({
        "service": "marketcore-os",
        "status": "READY",
        "version": APP_VERSION,
        "runtime_changed": 0,
        "execution_changed": 0,
        "orders_changed": 0,
        "fills_changed": 0,
        "micro_live_allowed": 0,
    })
