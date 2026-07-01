from __future__ import annotations

from dataclasses import dataclass, field

from marketcore.presentation.dashboard.layout import render_shell
from marketcore.presentation.widgets.common.responsive import Responsive
from marketcore.presentation.design_system.layout.grid import SectionHeader, DashboardGrid
from marketcore.presentation.design_system.components.cards import KeyValueCard


@dataclass(frozen=True)
class DashboardAction:
    label: str
    href: str


@dataclass(frozen=True)
class DashboardSection:
    title: str
    cards: list[str] = field(default_factory=list)

    def render(self) -> str:
        return SectionHeader(self.title) + DashboardGrid(self.cards)


@dataclass(frozen=True)
class DashboardPageContext:
    lang: str = "ru"
    timezone: str = "Europe/Moscow"


class BaseDashboardPage:
    page_key = "base"
    title = "Dashboard"
    subtitle = "MarketCore"
    actions: list[DashboardAction] = []

    def sections(self) -> list[DashboardSection]:
        return [
            DashboardSection(
                title="Base Page",
                cards=[
                    KeyValueCard(
                        "Status",
                        {
                            "Page": self.page_key,
                            "State": "READY",
                        },
                    )
                ],
            )
        ]

    def render_body(self) -> str:
        action_html = "".join(
            f'<a class="fc-nav-item" href="{a.href}">{a.label}</a>'
            for a in self.actions
        )

        header = (
            f'<section class="fc-card">'
            f'<h1>{self.title}</h1>'
            f'<p>{self.subtitle}</p>'
            f'<div>{action_html}</div>'
            f'</section>'
        )

        return header + "".join(section.render() for section in self.sections())

    def render(self, context: DashboardPageContext | None = None) -> str:
        context = context or DashboardPageContext()
        body = Responsive.css() + self.render_body()

        return render_shell(
            body,
            lang=context.lang,
            timezone=context.timezone,
        )
