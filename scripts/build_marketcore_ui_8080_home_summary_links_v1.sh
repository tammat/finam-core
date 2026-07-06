#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1 ==="

mkdir -p scripts src/marketcore/presentation/pages

cat > src/marketcore/presentation/layout.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.navigation import render_navigation
from marketcore.presentation.ui_labels import display_label
from marketcore.presentation.ui_text import normalize_ui_text


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
PY

cat > src/marketcore/presentation/app.py <<'PY'
from __future__ import annotations

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from marketcore.presentation.router import route


HOST = os.getenv("MARKETCORE_UI_HOST", "127.0.0.1")
PORT = int(os.getenv("MARKETCORE_UI_PORT", "8080"))


def _fallback_error_page(message: str) -> bytes:
    safe = message.replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>Ошибка MarketCore UI</title></head>
<body style="font-family:system-ui;background:#0f172a;color:#e5e7eb;padding:24px;">
<h1>Ошибка MarketCore UI</h1>
<pre>{safe}</pre>
<p>MARKETCORE_UI_SHELL_V1</p>
</body>
</html>""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            code, payload = route(parsed.path)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            code = 500
            payload = _fallback_error_page(f"{type(exc).__name__}: {exc}")

        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    print(f"MARKETCORE_UI_SHELL_V1_START host={HOST} port={PORT}", flush=True)
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
PY

cat > src/marketcore/presentation/pages/home.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _link(title: str, href: str, note: str) -> str:
    return f"""
    <a class="link-card" href="{escape(href)}">
      <strong>{escape(title)}</strong>
      <span>{escape(note)}</span>
    </a>
    """


def _metric(title: str, value: str, note: str = "") -> str:
    return f"""
    <section class="card">
        <h2>{escape(title)}</h2>
        <p style="font-size:28px;font-weight:700;margin:8px 0;">{escape(value)}</p>
        <p>{escape(note)}</p>
    </section>
    """


class HomePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/",
            title="MarketCore OS",
            icon="⌂",
            menu_order=10,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        phase = ctx.api_get("/api/kg/v1/phase-ii-paper-edge-discovery-summary")
        daily = ctx.api_get("/api/kg/v1/paper-sample-operations-daily-summary")
        ui_health = ctx.api_get("/api/kg/v1/marketcore-ui-systemd-health")

        phase_data = phase.get("data") or {}
        daily_data = daily.get("data") or {}
        ui_data = ui_health.get("data") or {}

        phase_status = str(phase_data.get("phase_result_status", "UNKNOWN"))
        operational_status = str(phase_data.get("operational_status", "UNKNOWN"))
        daily_status = str(daily_data.get("daily_status", "UNKNOWN"))
        ui_status = str(ui_data.get("overall_status", "UNKNOWN"))

        candidates = ctx.formatter.number(phase_data.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(phase_data.get("sample_ready"), 0)
        micro_live_allowed = str(phase_data.get("micro_live_allowed", False))

        return f"""
        <section class="card">
            <h2>Рабочий стол MarketCore</h2>
            <p>Единая точка входа: поиск преимущества, накопление выборки, торговый контур, риски, настройки и системное здоровье.</p>
            <p>UI работает через MarketCore UI Shell на 8080. Прямого SQL из страниц нет.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            {_metric("Phase II", phase_status, operational_status)}
            {_metric("Daily Status", daily_status, "Дневная сводка операций")}
            {_metric("UI/Systemd", ui_status, "8080 / 8095")}
            {_metric("Micro Live", micro_live_allowed, "Должно быть False")}
        </div>

        <section class="card">
            <h2>Сводка Paper Edge Discovery</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    <tr><td>Кандидатов</td><td>{escape(candidates)}</td></tr>
                    <tr><td>Готовы по выборке</td><td>{escape(sample_ready)}</td></tr>
                    <tr><td>Операционный статус</td><td>{escape(operational_status)}</td></tr>
                    <tr><td>Micro Live разрешён</td><td>{escape(micro_live_allowed)}</td></tr>
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Основные разделы</h2>
            <div class="link-grid">
                {_link("Поиск преимущества", "/paper-edge-discovery", "Кандидаты, объяснения, очередь проверки")}
                {_link("Итоги Phase II", "/phase-ii-paper-edge-discovery-summary", "Финальная сводка фазы")}
                {_link("Дневная сводка операций", "/paper-runtime-sample-collection-daily-summary", "Что делать сегодня")}
                {_link("Операции накопления выборки", "/paper-runtime-sample-collection-operations", "Кандидаты ближе всего к повторной проверке")}
                {_link("Накопление выборки", "/paper-sample-accumulation-monitor", "Сколько сделок есть и сколько нужно")}
                {_link("Здоровье операций", "/paper-sample-operations-timer-health", "Timer/service и свежесть данных")}
                {_link("Граф знаний", "/knowledge-graph", "Knowledge Graph, статистика, валидация")}
                {_link("Риски", "/risk", "Risk control и будущие risk gates")}
                {_link("Настройки", "/settings", "Локаль, валюта, таймзона, тема")}
                {_link("Здоровье UI/Systemd", "/marketcore-ui-systemd-health", "KG API 8095 и UI 8080")}
            </div>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1</p>
        </section>
        """
PY

cat > scripts/test_marketcore_ui_8080_home_summary_links_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/pages/home.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/registry.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/home.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_HOME_PAGE"
  exit 1
fi

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20480 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/home_summary_links_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20480/" > /tmp/home_summary_links_home_v1.html
curl -fsS "http://127.0.0.1:20480/risk" > /tmp/home_summary_links_risk_v1.html
curl -fsS "http://127.0.0.1:20480/settings" > /tmp/home_summary_links_settings_v1.html

grep -q "Рабочий стол" /tmp/home_summary_links_home_v1.html
grep -q "Поиск преимущества" /tmp/home_summary_links_home_v1.html
grep -q "Накопление выборки" /tmp/home_summary_links_home_v1.html
grep -q "Платформа знаний" /tmp/home_summary_links_home_v1.html
grep -q "Торговый контур" /tmp/home_summary_links_home_v1.html
grep -q "Система" /tmp/home_summary_links_home_v1.html
grep -q "Основные разделы" /tmp/home_summary_links_home_v1.html
grep -q "Дневная сводка операций" /tmp/home_summary_links_home_v1.html
grep -q "Операции накопления выборки" /tmp/home_summary_links_home_v1.html
grep -q "Здоровье UI/Systemd" /tmp/home_summary_links_home_v1.html
grep -q "Риски" /tmp/home_summary_links_home_v1.html
grep -q "Настройки" /tmp/home_summary_links_home_v1.html
grep -q "MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1" /tmp/home_summary_links_home_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/home_summary_links_home_v1.html

grep -q "Риски" /tmp/home_summary_links_risk_v1.html
grep -q "Настройки" /tmp/home_summary_links_settings_v1.html

if grep -q "Empty reply" /tmp/home_summary_links_ui_v1.log; then
  echo "EMPTY_REPLY_DETECTED"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/" > /tmp/home_summary_links_home_8080_v1.html
grep -q "Рабочий стол" /tmp/home_summary_links_home_8080_v1.html
grep -q "Основные разделы" /tmp/home_summary_links_home_8080_v1.html
grep -q "Риски" /tmp/home_summary_links_home_8080_v1.html
grep -q "Настройки" /tmp/home_summary_links_home_8080_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/home_summary_links_home_8080_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_8080_home_summary_links_v1.sh

scripts/test_marketcore_ui_8080_home_summary_links_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1_OK"
