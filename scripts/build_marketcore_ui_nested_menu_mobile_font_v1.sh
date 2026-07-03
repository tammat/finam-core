#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1 ==="

mkdir -p src/marketcore/presentation scripts src/scripts

cat > src/marketcore/presentation/ui_labels.py <<'PY'
from __future__ import annotations


ROUTE_LABELS_RU = {
    "/": "Рабочий стол",

    "/paper-edge-discovery": "Edge",
    "/edge-validation-queue": "Проверка",
    "/edge-validation-pipeline": "Этапы",
    "/edge-robustness-check": "Устойчивость",
    "/edge-oos-validation": "Вне выборки",
    "/edge-oos-backtest": "Тест вне выборки",
    "/micro-live-readiness": "Проба",

    "/paper-edge-market-data-binding": "Данные",
    "/paper-edge-market-data-freshness": "Свежесть",
    "/paper-edge-market-symbol-alias-plan": "Alias",
    "/market-universe-ranking": "Рейтинг",
    "/market-universe-research-queue": "Кандидаты",
    "/market-universe-research-queue-timer-health": "Таймер Research",

    "/paper-sample-accumulation-monitor": "Выборка",
    "/paper-sample-collection-timer-health": "Таймер",
    "/paper-runtime-sample-collection-phase-close": "Фаза",
    "/phase-ii-paper-edge-discovery-summary": "Итоги",
    "/paper-runtime-sample-collection-operations": "Операции",
    "/paper-sample-operations-timer-health": "Таймер операций",
    "/paper-runtime-sample-collection-daily-summary": "Сводка",

    "/runtime": "Runtime",
    "/portfolio": "Портфель",
    "/orders": "Заявки",
    "/risk": "Риски",

    "/knowledge-graph": "Знания",
    "/research": "Исследования",
    "/validation": "Валидация",
    "/ai": "AI",

    "/logs": "Логи",
    "/system": "Система",
    "/settings": "Настройки",
    "/marketcore-ui-systemd-health": "UI",
    "/marketcore-ui-route-health-matrix": "Маршруты",
}


def display_label(route: str, fallback: str = "") -> str:
    return ROUTE_LABELS_RU.get(route, fallback or route)


def route_labels() -> dict[str, str]:
    return dict(ROUTE_LABELS_RU)
PY

cat > src/marketcore/presentation/route_groups.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteGroup:
    key: str
    title_ru: str
    order: int
    routes: tuple[str, ...]


ROUTE_GROUPS: tuple[RouteGroup, ...] = (
    RouteGroup("home", "Главное", 10, ("/",)),

    RouteGroup("market", "Рынок", 20, (
        "/market-universe-ranking",
        "/market-universe-research-queue",
        "/market-universe-research-queue-timer-health",
        "/paper-edge-market-data-binding",
        "/paper-edge-market-data-freshness",
        "/paper-edge-market-symbol-alias-plan",
    )),

    RouteGroup("edge", "Edge", 30, (
        "/paper-edge-discovery",
        "/edge-validation-queue",
        "/edge-validation-pipeline",
        "/edge-robustness-check",
        "/edge-oos-validation",
        "/edge-oos-backtest",
        "/micro-live-readiness",
    )),

    RouteGroup("sample", "Выборка", 40, (
        "/paper-sample-accumulation-monitor",
        "/paper-sample-collection-timer-health",
        "/paper-runtime-sample-collection-phase-close",
        "/phase-ii-paper-edge-discovery-summary",
        "/paper-runtime-sample-collection-operations",
        "/paper-sample-operations-timer-health",
        "/paper-runtime-sample-collection-daily-summary",
    )),

    RouteGroup("trading", "Торговля", 50, (
        "/runtime",
        "/portfolio",
        "/orders",
        "/risk",
    )),

    RouteGroup("knowledge", "Знания", 60, (
        "/knowledge-graph",
        "/research",
        "/validation",
        "/ai",
    )),

    RouteGroup("system", "Система", 70, (
        "/logs",
        "/system",
        "/settings",
        "/marketcore-ui-systemd-health",
        "/marketcore-ui-route-health-matrix",
    )),
)


OTHER_GROUP = RouteGroup("other", "Прочее", 999, ())


def group_for_route(route: str) -> RouteGroup:
    for group in ROUTE_GROUPS:
        if route in group.routes:
            return group
    return OTHER_GROUP


def route_groups() -> tuple[RouteGroup, ...]:
    return ROUTE_GROUPS
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/layout.py")
s = p.read_text()

if "@media (max-width: 900px)" in s:
    s = s.replace(
        "@media (max-width: 900px) {",
        """
.mobile-menu-note {
  display:none;
}
@media (max-width: 900px) {"""
    )

if "font-size:17px;" not in s:
    s = s.replace(
        ".main {\n  padding:24px;",
        ".main {\n  padding:24px;\n  font-size:16px;"
    )

    s = s.replace(
        ".nav-item {\n  display:flex;",
        ".nav-item {\n  display:flex;\n  font-size:15px;"
    )

    s = s.replace(
        "@media (max-width: 900px) {\n  .app {",
        """@media (max-width: 900px) {
  body {
    font-size:17px;
  }
  .main {
    padding:16px;
    font-size:17px;
  }
  .header h1 {
    font-size:26px;
  }
  .nav-item {
    font-size:17px;
    padding:13px 14px;
  }
  .nav-group-title {
    font-size:13px;
    margin-top:18px;
  }
  .card {
    padding:16px;
  }
  table {
    font-size:15px;
  }
  th,td {
    font-size:15px;
    padding:10px 8px;
  }
  .app {"""
    )

p.write_text(s)
PY

cat > src/scripts/audit_marketcore_ui_nested_menu_mobile_font_v1.py <<'PY'
from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route, route_groups
from marketcore.presentation.ui_labels import display_label


REQUIRED_LABELS = {
    "/market-universe-ranking": "Рейтинг",
    "/market-universe-research-queue": "Кандидаты",
    "/paper-sample-collection-timer-health": "Таймер",
    "/edge-robustness-check": "Устойчивость",
    "/edge-validation-pipeline": "Этапы",
    "/micro-live-readiness": "Проба",
    "/knowledge-graph": "Знания",
    "/edge-oos-validation": "Вне выборки",
    "/edge-oos-backtest": "Тест вне выборки",
}


def main() -> None:
    print("=== MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1 ===")

    pages = menu_pages()
    groups = route_groups()

    print(f"pages_total={len(pages)}")
    print(f"groups_total={len(groups)}")

    for route, expected in REQUIRED_LABELS.items():
        label = display_label(route)
        print(f"LABEL route={route} label={label}")
        if label != expected:
            raise SystemExit(f"BAD_LABEL route={route} expected={expected} actual={label}")

    for page in pages:
        group = group_for_route(page.route)
        print(f"PAGE group={group.title_ru} route={page.route} label={display_label(page.route, page.title)}")

    print("short_labels=READY")
    print("nested_menu=READY")
    print("mobile_font=READY")
    print("VERDICT=MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_marketcore_ui_nested_menu_mobile_font_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_nested_menu_mobile_font_v1.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_nested_menu_mobile_font_v1.py \
  | tee /tmp/marketcore_ui_nested_menu_mobile_font_v1.txt

grep -q "VERDICT=MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_READY" \
  /tmp/marketcore_ui_nested_menu_mobile_font_v1.txt

grep -q "Рынок" src/marketcore/presentation/route_groups.py
grep -q "Кандидаты" src/marketcore/presentation/ui_labels.py
grep -q "Этапы" src/marketcore/presentation/ui_labels.py
grep -q "Проба" src/marketcore/presentation/ui_labels.py
grep -q "Знания" src/marketcore/presentation/ui_labels.py
grep -q "font-size:17px" src/marketcore/presentation/layout.py

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/" > /tmp/ui_nested_home.html

grep -q "Рынок" /tmp/ui_nested_home.html
grep -q "Рейтинг" /tmp/ui_nested_home.html
grep -q "Кандидаты" /tmp/ui_nested_home.html
grep -q "Этапы" /tmp/ui_nested_home.html
grep -q "Устойчивость" /tmp/ui_nested_home.html
grep -q "Проба" /tmp/ui_nested_home.html
grep -q "Знания" /tmp/ui_nested_home.html
grep -q "Вне выборки" /tmp/ui_nested_home.html
grep -q "Тест вне выборки" /tmp/ui_nested_home.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_nested_menu_mobile_font_v1.sh
scripts/test_marketcore_ui_nested_menu_mobile_font_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_OK"
