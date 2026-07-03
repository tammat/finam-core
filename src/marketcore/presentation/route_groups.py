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
