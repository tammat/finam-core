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
