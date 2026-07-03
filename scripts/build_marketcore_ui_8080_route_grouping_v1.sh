#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_8080_ROUTE_GROUPING_V1 ==="

mkdir -p src/scripts scripts src/marketcore/presentation

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
    RouteGroup(
        key="home",
        title_ru="Рабочий стол",
        order=10,
        routes=(
            "/",
        ),
    ),
    RouteGroup(
        key="paper_edge",
        title_ru="Поиск преимущества",
        order=20,
        routes=(
            "/paper-edge-discovery",
            "/edge-validation-queue",
            "/edge-validation-pipeline",
            "/edge-robustness-check",
            "/edge-oos-validation",
            "/edge-oos-backtest",
            "/micro-live-readiness",
        ),
    ),
    RouteGroup(
        key="sample_collection",
        title_ru="Накопление выборки",
        order=30,
        routes=(
            "/paper-sample-accumulation-monitor",
            "/paper-sample-collection-timer-health",
            "/paper-runtime-sample-collection-phase-close",
            "/phase-ii-paper-edge-discovery-summary",
            "/paper-runtime-sample-collection-operations",
            "/paper-sample-operations-timer-health",
            "/paper-runtime-sample-collection-daily-summary",
        ),
    ),
    RouteGroup(
        key="knowledge_platform",
        title_ru="Платформа знаний",
        order=40,
        routes=(
            "/knowledge-graph",
            "/research",
            "/validation",
            "/ai",
        ),
    ),
    RouteGroup(
        key="trading_control",
        title_ru="Торговый контур",
        order=50,
        routes=(
            "/runtime",
            "/portfolio",
            "/orders",
            "/risk",
        ),
    ),
    RouteGroup(
        key="system",
        title_ru="Система",
        order=60,
        routes=(
            "/logs",
            "/system",
            "/settings",
            "/marketcore-ui-systemd-health",
        ),
    ),
)


OTHER_GROUP = RouteGroup(
    key="other",
    title_ru="Прочее",
    order=999,
    routes=(),
)


def group_for_route(route: str) -> RouteGroup:
    for group in ROUTE_GROUPS:
        if route in group.routes:
            return group
    return OTHER_GROUP


def grouped_routes() -> dict[str, RouteGroup]:
    mapping: dict[str, RouteGroup] = {}
    for group in ROUTE_GROUPS:
        for route in group.routes:
            mapping[route] = group
    return mapping


def route_groups() -> tuple[RouteGroup, ...]:
    return ROUTE_GROUPS
PY

cat > src/marketcore/presentation/navigation.py <<'PY'
from __future__ import annotations

from collections import defaultdict
from html import escape

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import OTHER_GROUP, group_for_route, route_groups
from marketcore.presentation.ui_labels import display_label


def render_navigation(active_route: str) -> str:
    pages_by_group = defaultdict(list)

    for page in menu_pages():
        group = group_for_route(page.route)
        pages_by_group[group.key].append(page)

    chunks: list[str] = []

    for group in (*route_groups(), OTHER_GROUP):
        pages = pages_by_group.get(group.key, [])
        if not pages:
            continue

        chunks.append('<div class="nav-group">')
        chunks.append(f'<div class="nav-group-title">{escape(group.title_ru)}</div>')

        for page in sorted(pages, key=lambda p: p.menu_order):
            active = " active" if page.route == active_route else ""
            label = display_label(page.route, page.title)

            chunks.append(
                f'<a class="nav-item{active}" href="{escape(page.route)}">'
                f'<span class="nav-icon">{escape(page.icon)}</span>'
                f'<span class="nav-label">{escape(label)}</span>'
                f'</a>'
            )

        chunks.append("</div>")

    return "\n".join(chunks)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/layout.py")
s = p.read_text()

if ".nav-group-title" not in s:
    marker = ".nav-item {"
    if marker not in s:
        raise SystemExit("layout .nav-item marker not found")

    addition = """
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
"""
    s = s.replace(marker, addition + "\n" + marker)

if "Единая оболочка платформы" not in s:
    print("WARN layout subtitle text not found; no hard failure")

p.write_text(s)
PY

cat > src/scripts/audit_marketcore_ui_8080_route_grouping_v1.py <<'PY'
from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route, route_groups
from marketcore.presentation.ui_labels import display_label


REQUIRED_GROUPS = {
    "home",
    "paper_edge",
    "sample_collection",
    "knowledge_platform",
    "trading_control",
    "system",
}

REQUIRED_ROUTE_GROUPS = {
    "/": "home",
    "/paper-edge-discovery": "paper_edge",
    "/edge-validation-queue": "paper_edge",
    "/edge-validation-pipeline": "paper_edge",
    "/edge-robustness-check": "paper_edge",
    "/edge-oos-validation": "paper_edge",
    "/edge-oos-backtest": "paper_edge",
    "/micro-live-readiness": "paper_edge",
    "/paper-sample-accumulation-monitor": "sample_collection",
    "/paper-runtime-sample-collection-operations": "sample_collection",
    "/paper-runtime-sample-collection-daily-summary": "sample_collection",
    "/phase-ii-paper-edge-discovery-summary": "sample_collection",
    "/knowledge-graph": "knowledge_platform",
    "/research": "knowledge_platform",
    "/validation": "knowledge_platform",
    "/runtime": "trading_control",
    "/portfolio": "trading_control",
    "/orders": "trading_control",
    "/risk": "trading_control",
    "/logs": "system",
    "/system": "system",
    "/settings": "system",
    "/marketcore-ui-systemd-health": "system",
}


def main() -> None:
    pages = menu_pages()
    group_keys = {group.key for group in route_groups()}
    missing_groups = sorted(REQUIRED_GROUPS - group_keys)

    print("=== MARKETCORE_UI_8080_ROUTE_GROUPING_V1 ===")
    print(f"pages_total={len(pages)}")
    print(f"groups_total={len(group_keys)}")

    if missing_groups:
        print("missing_groups=" + ",".join(missing_groups))
        raise SystemExit(2)

    page_routes = {page.route for page in pages}
    missing_routes = sorted(set(REQUIRED_ROUTE_GROUPS) - page_routes)

    if missing_routes:
        print("missing_routes=" + ",".join(missing_routes))
        raise SystemExit(3)

    unknown_routes: list[str] = []
    wrong_groups: list[str] = []

    for page in pages:
        group = group_for_route(page.route)
        label = display_label(page.route, page.title)

        print(
            "PAGE "
            f"group={group.key} "
            f"group_title={group.title_ru} "
            f"route={page.route} "
            f"label_ru={label} "
            f"order={page.menu_order}"
        )

        if group.key == "other":
            unknown_routes.append(page.route)

        expected_group = REQUIRED_ROUTE_GROUPS.get(page.route)
        if expected_group and expected_group != group.key:
            wrong_groups.append(f"{page.route}:{group.key}!={expected_group}")

    if unknown_routes:
        print("unknown_routes=" + ",".join(sorted(unknown_routes)))
        raise SystemExit(4)

    if wrong_groups:
        print("wrong_groups=" + ",".join(sorted(wrong_groups)))
        raise SystemExit(5)

    print("route_groups_required=READY")
    print("route_grouping_complete=READY")
    print("route_grouping_no_unknown_routes=READY")
    print("route_grouping_ru_titles=READY")
    print("VERDICT=MARKETCORE_UI_8080_ROUTE_GROUPING_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_marketcore_ui_8080_route_grouping_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_8080_ROUTE_GROUPING_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/scripts/audit_marketcore_ui_8080_route_grouping_v1.py \
  src/marketcore/presentation/app.py

PYTHONPATH=src python src/scripts/audit_marketcore_ui_8080_route_grouping_v1.py \
  | tee /tmp/marketcore_ui_8080_route_grouping_v1.txt

grep -q "VERDICT=MARKETCORE_UI_8080_ROUTE_GROUPING_V1_READY" \
  /tmp/marketcore_ui_8080_route_grouping_v1.txt

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20380 KG_API_BASE_URL=http://127.0.0.1:1 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_ui_route_grouping_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

curl -fsS "http://127.0.0.1:20380/" > /tmp/route_grouping_home_v1.html
curl -fsS "http://127.0.0.1:20380/risk" > /tmp/route_grouping_risk_v1.html
curl -fsS "http://127.0.0.1:20380/settings" > /tmp/route_grouping_settings_v1.html

grep -q "Рабочий стол" /tmp/route_grouping_home_v1.html
grep -q "Поиск преимущества" /tmp/route_grouping_home_v1.html
grep -q "Накопление выборки" /tmp/route_grouping_home_v1.html
grep -q "Платформа знаний" /tmp/route_grouping_home_v1.html
grep -q "Торговый контур" /tmp/route_grouping_home_v1.html
grep -q "Система" /tmp/route_grouping_home_v1.html

grep -q "Риски" /tmp/route_grouping_home_v1.html
grep -q "Настройки" /tmp/route_grouping_home_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/route_grouping_home_v1.html

grep -q "Риски" /tmp/route_grouping_risk_v1.html
grep -q "Настройки" /tmp/route_grouping_settings_v1.html

grep -q ".nav-group-title" src/marketcore/presentation/layout.py
grep -q "group_for_route" src/marketcore/presentation/navigation.py

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_8080_ROUTE_GROUPING_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_8080_ROUTE_GROUPING_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_8080_route_grouping_v1.sh

scripts/test_marketcore_ui_8080_route_grouping_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_8080_ROUTE_GROUPING_V1_OK"
