#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_MARKETCORE_UI_MENU_CLEANUP_V1_FIX_REQUIRED_ROUTES ==="

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
    RouteGroup("home", "Главная", 10, ("/",)),

    RouteGroup("research", "Исследования", 20, (
        "/edge-factory",
        "/max-edge",
        "/edge-score-shadow",
        "/edge-score-shadow-daily",
        "/research",
    )),

    RouteGroup("market", "Рынок", 30, (
        "/market-model",
        "/market-universe-ranking",
        "/market-universe-research-queue",
        "/knowledge-graph",
    )),

    RouteGroup("portfolio", "Портфель", 40, (
        "/portfolio",
        "/risk",
    )),

    RouteGroup("data", "Данные", 50, (
        "/feature-store",
        "/validation",
    )),

    RouteGroup("system", "Система", 90, (
        "/system",
        "/logs",
        "/settings",
    )),
)


OTHER_GROUP = RouteGroup("other", "Инженерный режим", 999, ())


def group_for_route(route: str) -> RouteGroup:
    for group in ROUTE_GROUPS:
        if route in group.routes:
            return group
    return OTHER_GROUP


def route_groups() -> tuple[RouteGroup, ...]:
    return ROUTE_GROUPS
PY

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/ui_labels.py")
s = p.read_text(encoding="utf-8")

required = {
    "/": "Рабочий стол",
    "/edge-factory": "Фабрика Edge",
    "/max-edge": "Лучший Edge",
    "/edge-score-shadow": "Shadow-наблюдение",
    "/edge-score-shadow-daily": "Ежедневная аналитика",
    "/research": "Исследования",
    "/market-model": "Модель рынка",
    "/market-universe-ranking": "Рейтинг рынка",
    "/market-universe-research-queue": "Очередь исследований",
    "/knowledge-graph": "Граф знаний",
    "/portfolio": "Портфель",
    "/risk": "Риски",
    "/feature-store": "Признаки",
    "/validation": "Проверка",
    "/system": "Система",
    "/logs": "Журнал",
    "/settings": "Настройки",
}

start = s.find("ROUTE_LABELS_RU = {")
if start < 0:
    raise SystemExit("ROUTE_LABELS_RU_NOT_FOUND")

end = s.find("\n}\n\n\ndef display_label", start)
if end < 0:
    raise SystemExit("ROUTE_LABELS_RU_END_NOT_FOUND")

body = "ROUTE_LABELS_RU = {\n"
for route, label in required.items():
    body += f'    "{route}": "{label}",\n'
body += "}"

s = s[:start] + body + s[end + 2:]
p.write_text(s, encoding="utf-8")
PY

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_menu_cleanup \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/registry_autodiscovery.py

echo "VERDICT=MARKETCORE_UI_MENU_CLEANUP_V1_FIX_REQUIRED_ROUTES_READY"
