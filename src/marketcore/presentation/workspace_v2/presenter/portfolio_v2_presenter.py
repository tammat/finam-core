from __future__ import annotations

from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import CardType, SectionType, UiStatusCode, WidgetType
from marketcore.presentation.workspace_v2.formatter.portfolio_v2_formatter import PortfolioV2Formatter
from marketcore.presentation.workspace_v2.resolver.portfolio_v2_resolver import PortfolioV2Resolver
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import PortfolioV2ViewModel


class PortfolioV2Presenter:
    def __init__(self) -> None:
        self._resolver = PortfolioV2Resolver()
        self._formatter = PortfolioV2Formatter()

    def load(self, limit: int = 200) -> PortfolioV2ViewModel:
        snapshot = self._resolver.resolve(limit=limit)

        sections = (
            self._section("summary", SectionType.SUMMARY, snapshot.summary, 10),
            self._section("positions", SectionType.PORTFOLIO, snapshot.positions, 20),
            self._section("dashboard", SectionType.PORTFOLIO, snapshot.dashboard, 30),
            self._section("visualization", SectionType.PORTFOLIO, snapshot.visualization, 40),
        )

        return PortfolioV2ViewModel(
            title_key="portfolio.workspace.title",
            subtitle_key="portfolio.workspace.subtitle",
            sections=sections,
        )

    def _section(self, section_code: str, section_type: SectionType, rows: tuple, order: int) -> BaseSection:
        cards = tuple(
            self._card(row.source_view, row.values, index)
            for index, row in enumerate(rows, start=1)
        )

        return BaseSection(
            section_id=self._formatter.section_id(section_code),
            section_type=section_type,
            title_key=f"portfolio.section.{section_code}.title",
            subtitle_key=f"portfolio.section.{section_code}.subtitle",
            tooltip_key=f"portfolio.section.{section_code}.tooltip",
            order=order,
            status_code=UiStatusCode.OK if cards else UiStatusCode.WARNING,
            status_label_key="ui.status.ok" if cards else "ui.status.warning",
            cards=cards,
        )

    def _card(self, source_view: str, values: dict, index: int) -> BaseCard:
        return BaseCard(
            widget_id=self._formatter.card_id(source_view, index),
            widget_type=WidgetType.BASE,
            card_type=CardType.BASE,
            title_key=self._formatter.source_key(source_view),
            subtitle_key="portfolio.card.subtitle",
            tooltip_key="portfolio.card.tooltip",
            status_code=UiStatusCode.OK,
            status_label_key="ui.status.ok",
            priority=index,
            payload={
                "source_view": source_view,
                "values": values,
                "column_keys": {
                    column_name: self._formatter.column_key(column_name)
                    for column_name in values.keys()
                },
            },
        )
