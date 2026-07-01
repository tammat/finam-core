from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from marketcore.presentation.pages.base_page import BaseDashboardPage, DashboardPageContext, DashboardSection
from marketcore.presentation.design_system.components.cards import KeyValueCard, MetricCard, StatusCard, VersionCard
from marketcore.services.dashboard.executive_overview_service import ExecutiveOverviewService

home_router = APIRouter()


class ExecutiveOverviewPage(BaseDashboardPage):
    page_key = "executive_overview"
    title = "MarketCore"
    subtitle = "Trading Intelligence Platform v1.0.0"

    def __init__(self) -> None:
        self.vm = ExecutiveOverviewService().load()

    def sections(self) -> list[DashboardSection]:
        vm = self.vm

        return [
            DashboardSection(
                title="Главная",
                cards=[
                    MetricCard("Система", vm.health_value, vm.health_status),
                    StatusCard("Риски", vm.risk.value),
                    KeyValueCard(
                        "Приоритет",
                        {
                            "Риск": vm.risk.reason,
                            "План": vm.risk.priority,
                        },
                    ),
                ],
            ),
            DashboardSection(
                title="Платформа",
                cards=[
                    MetricCard(item.title, item.value, item.status)
                    for item in vm.platform
                ],
            ),
            DashboardSection(
                title="Рынок",
                cards=[
                    MetricCard(item.title, item.value, item.status)
                    for item in vm.market
                ],
            ),
            DashboardSection(
                title="Исслед.",
                cards=[
                    MetricCard(item.title, item.value, item.status)
                    for item in vm.research
                ],
            ),
            DashboardSection(
                title="Мета",
                cards=[
                    MetricCard(item.title, item.value, item.status)
                    for item in vm.metadata
                ],
            ),
            DashboardSection(
                title="Выполн.",
                cards=[
                    MetricCard(item.title, item.value, item.status)
                    for item in vm.execution
                ],
            ),
            DashboardSection(
                title="Версия",
                cards=[
                    VersionCard(vm.version.product_name, vm.version.product_version),
                    KeyValueCard(
                        "Версии",
                        {
                            "Dashboard": vm.version.dashboard_version,
                            "Repo": vm.version.repo,
                            "Commit": vm.version.git_commit,
                            "Tag": vm.version.git_tag,
                        },
                    ),
                ],
            ),
            DashboardSection(
                title="События",
                cards=[
                    KeyValueCard(
                        "Последние",
                        {
                            item.time_label: item.text
                            for item in vm.activity[:4]
                        },
                    )
                ],
            ),
            DashboardSection(
                title="Быстрые действия",
                cards=[
                    MetricCard(item.title, item.value, item.status)
                    for item in vm.quick_actions
                ],
            ),
        ]


@home_router.get("/", response_class=HTMLResponse)
def executive_overview(
    lang: str = Query(default="ru"),
    timezone: str = Query(default="Europe/Moscow"),
) -> HTMLResponse:
    page = ExecutiveOverviewPage()
    return HTMLResponse(
        page.render(
            DashboardPageContext(
                lang=lang,
                timezone=timezone,
            )
        )
    )


@home_router.get("/api/home")
def executive_overview_api() -> dict[str, object]:
    vm = ExecutiveOverviewService().load()
    return asdict(vm)
