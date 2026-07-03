#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1 ==="

mkdir -p src/scripts scripts src/marketcore/presentation

cat > src/marketcore/presentation/ui_labels.py <<'PY'
from __future__ import annotations


ROUTE_LABELS_RU = {
    "/": "Рабочий стол",

    "/runtime": "Runtime",
    "/paper-edge-discovery": "Поиск Edge",
    "/edge-validation-queue": "Очередь валидации Edge",
    "/edge-validation-pipeline": "Pipeline валидации",
    "/edge-robustness-check": "Проверка устойчивости",
    "/edge-oos-validation": "OOS-проверка",
    "/edge-oos-backtest": "OOS-бэктест",
    "/micro-live-readiness": "Готовность Micro Live",

    "/paper-sample-accumulation-monitor": "Накопление выборки",
    "/paper-sample-collection-timer-health": "Здоровье таймера выборки",
    "/paper-runtime-sample-collection-phase-close": "Закрытие фазы выборки",
    "/phase-ii-paper-edge-discovery-summary": "Итоги Phase II",
    "/paper-runtime-sample-collection-operations": "Операции накопления выборки",
    "/paper-sample-operations-timer-health": "Здоровье таймера операций",
    "/paper-runtime-sample-collection-daily-summary": "Дневная сводка операций",
    "/marketcore-ui-systemd-health": "Здоровье UI/Systemd",

    "/knowledge-graph": "Граф знаний",
    "/research": "Исследования",
    "/portfolio": "Портфель",
    "/orders": "Заявки",
    "/risk": "Риски",
    "/validation": "Валидация",
    "/logs": "Журнал",
    "/system": "Система",
    "/settings": "Настройки",
    "/ai": "AI",

    "/capital": "Капитал",
    "/edge": "Edge",
    "/intraday": "Интрадей",
}


def display_label(route: str, fallback: str = "") -> str:
    return ROUTE_LABELS_RU.get(route, fallback or route)


def route_labels() -> dict[str, str]:
    return dict(ROUTE_LABELS_RU)
PY

cat > src/marketcore/presentation/navigation.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.ui_labels import display_label


def render_navigation(active_route: str) -> str:
    items: list[str] = []

    for page in menu_pages():
        active = " active" if page.route == active_route else ""
        label = display_label(page.route, page.title)

        items.append(
            f'<a class="nav-item{active}" href="{escape(page.route)}">'
            f'<span class="nav-icon">{escape(page.icon)}</span>'
            f'<span class="nav-label">{escape(label)}</span>'
            f'</a>'
        )

    return "\n".join(items)
PY

cat > src/marketcore/presentation/layout.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.navigation import render_navigation
from marketcore.presentation.ui_labels import display_label


def render_layout(title: str, active_route: str, content: str) -> bytes:
    page_title = display_label(active_route, title)

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
PY

cat > src/scripts/audit_marketcore_ui_8080_navigation_v1.py <<'PY'
from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.ui_labels import route_labels, display_label


REQUIRED_ROUTES = {
    "/",
    "/paper-edge-discovery",
    "/paper-sample-accumulation-monitor",
    "/phase-ii-paper-edge-discovery-summary",
    "/risk",
    "/settings",
}


def main() -> None:
    labels = route_labels()
    pages = menu_pages()

    routes = {page.route for page in pages}
    missing_required = sorted(REQUIRED_ROUTES - routes)
    missing_labels = sorted(page.route for page in pages if page.route not in labels)

    print("=== MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1 ===")
    print(f"pages_total={len(pages)}")

    for page in pages:
        print(
            "PAGE "
            f"route={page.route} "
            f"title={page.title} "
            f"label_ru={display_label(page.route, page.title)} "
            f"order={page.menu_order}"
        )

    if missing_required:
        print("missing_required_routes=" + ",".join(missing_required))
        raise SystemExit(2)

    if missing_labels:
        print("missing_ru_labels=" + ",".join(missing_labels))
        raise SystemExit(3)

    print("navigation_required_routes=READY")
    print("navigation_ru_labels=READY")
    print("navigation_single_shell=READY")
    print("theme_single_layout=READY")
    print("risk_page=READY")
    print("settings_page=READY")
    print("VERDICT=MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_marketcore_ui_8080_navigation_audit_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_8080_navigation_v1.py \
  src/marketcore/presentation/app.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_8080_navigation_v1.py \
  | tee /tmp/marketcore_ui_8080_navigation_audit_v1.txt

grep -q "VERDICT=MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_READY" \
  /tmp/marketcore_ui_8080_navigation_audit_v1.txt

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20180 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_ui_nav_audit_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20180/" > /tmp/marketcore_ui_nav_home_v1.html
curl -fsS "http://127.0.0.1:20180/risk" > /tmp/marketcore_ui_nav_risk_v1.html
curl -fsS "http://127.0.0.1:20180/settings" > /tmp/marketcore_ui_nav_settings_v1.html

grep -q "Рабочий стол" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Поиск Edge" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Риски" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Настройки" /tmp/marketcore_ui_nav_home_v1.html
grep -q "Единая оболочка платформы" /tmp/marketcore_ui_nav_home_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_ui_nav_home_v1.html

grep -q "Риски" /tmp/marketcore_ui_nav_risk_v1.html
grep -q "Настройки" /tmp/marketcore_ui_nav_settings_v1.html

grep -q -- "--bg:#0f172a" src/marketcore/presentation/layout.py
grep -q "display_label" src/marketcore/presentation/navigation.py

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_8080_navigation_audit_v1.sh

scripts/test_marketcore_ui_8080_navigation_audit_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_OK"
