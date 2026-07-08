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
