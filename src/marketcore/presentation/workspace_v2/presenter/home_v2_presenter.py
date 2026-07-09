from __future__ import annotations

from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_layout import BaseLayout
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import (
    ActionCode,
    CardType,
    LayoutType,
    SectionType,
    UiStatusCode,
    WidgetType,
)
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import HomeV2ViewModel


class HomeV2Presenter:
    def load(self) -> HomeV2ViewModel:
        system_section = BaseSection(
            section_id="home.section.system",
            section_type=SectionType.SUMMARY,
            title_key="home.section.system.title",
            subtitle_key="home.section.system.subtitle",
            order=10,
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            cards=(
                BaseCard(
                    widget_id="home.card.system.status",
                    widget_type=WidgetType.BASE,
                    card_type=CardType.KPI,
                    title_key="home.card.system.status.title",
                    subtitle_key="home.card.system.status.subtitle",
                    status_code=UiStatusCode.WARNING,
                    status_label_key="ui.status.warning",
                    priority=10,
                ),
            ),
        )

        status_section = BaseSection(
            section_id="home.section.status",
            section_type=SectionType.SUMMARY,
            title_key="home.section.status.title",
            subtitle_key="home.section.status.subtitle",
            order=15,
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            cards=(
                self._status_card("home.card.status.system", "home.card.status.system.title", "home.card.status.ready.subtitle", UiStatusCode.OK, 10),
                self._status_card("home.card.status.portfolio", "home.card.status.portfolio.title", "home.card.status.ready.subtitle", UiStatusCode.OK, 20),
                self._status_card("home.card.status.research", "home.card.status.research.title", "home.card.status.pending.subtitle", UiStatusCode.WARNING, 30),
                self._status_card("home.card.status.probe", "home.card.status.probe.title", "home.card.status.pending.subtitle", UiStatusCode.WARNING, 40),
                self._status_card("home.card.status.observation", "home.card.status.observation.title", "home.card.status.pending.subtitle", UiStatusCode.WARNING, 50),
                self._status_card("home.card.status.runtime", "home.card.status.runtime.title", "home.card.status.blocked.subtitle", UiStatusCode.BLOCKED, 60),
            ),
        )

        navigation_section = BaseSection(
            section_id="home.section.navigation",
            section_type=SectionType.ACTIONS,
            title_key="home.section.navigation.title",
            subtitle_key="home.section.navigation.subtitle",
            order=20,
            status_code=UiStatusCode.OK,
            status_label_key="ui.status.ok",
            cards=(
                self._nav_card("home.card.portfolio", "home.card.portfolio.title", "/workspace-v2/portfolio", 10),
                self._nav_card("home.card.portfolio.phone", "home.card.portfolio.phone.title", "/workspace-v2/portfolio/phone", 15),
                self._nav_card("home.card.probe", "home.card.probe.title", "/workspace-v2/probe", 20),
                self._nav_card("home.card.research", "home.card.research.title", "/workspace-v2/research", 30),
                self._nav_card("home.card.runtime", "home.card.runtime.title", "/runtime", 40),
            ),
        )

        layout = BaseLayout(
            layout_id="home.layout.desktop",
            layout_type=LayoutType.DESKTOP,
            title_key="home.workspace.title",
            subtitle_key="home.workspace.subtitle",
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            sections=(system_section, status_section, navigation_section),
        )

        return HomeV2ViewModel(layout=layout)

    def _status_card(
        self,
        widget_id: str,
        title_key: str,
        subtitle_key: str,
        status_code: UiStatusCode,
        priority: int,
    ) -> BaseCard:
        return BaseCard(
            widget_id=widget_id,
            widget_type=WidgetType.BASE,
            card_type=CardType.KPI,
            title_key=title_key,
            subtitle_key=subtitle_key,
            status_code=status_code,
            status_label_key=(
                "ui.status.ok"
                if status_code == UiStatusCode.OK
                else "ui.status.warning"
                if status_code == UiStatusCode.WARNING
                else "ui.status.blocked"
            ),
            priority=priority,
        )

    def _nav_card(self, widget_id: str, title_key: str, target: str, priority: int) -> BaseCard:
        return BaseCard(
            widget_id=widget_id,
            widget_type=WidgetType.BASE,
            card_type=CardType.ACTION,
            title_key=title_key,
            subtitle_key="ui.action.open",
            status_code=UiStatusCode.OK,
            status_label_key="ui.status.ok",
            priority=priority,
            actions=(
                {"action_code": ActionCode.OPEN.value, "target": target},
            ),
        )
