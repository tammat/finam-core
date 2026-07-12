from __future__ import annotations

from numbers import Number

from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import CardType, SectionType, UiStatusCode, WidgetType
from marketcore.presentation.workspace_v2.formatter.portfolio_v2_formatter import PortfolioV2Formatter
from marketcore.presentation.workspace_v2.resolver.portfolio_v2_resolver import PortfolioV2Resolver
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import PortfolioV2ViewModel
from marketcore.presentation.services.operator_settings_v1 import OperatorSettingsV1
from marketcore.presentation.services.moex_index_service_v1 import MoexIndexServiceV1


class PortfolioV2Presenter:
    def __init__(self, settings: OperatorSettingsV1 | None = None) -> None:
        self._settings = settings or OperatorSettingsV1.load()
        self._resolver = PortfolioV2Resolver()
        self._formatter = PortfolioV2Formatter(self._settings)

    def load(self, limit: int = 200) -> PortfolioV2ViewModel:
        snapshot = self._resolver.resolve(limit=limit)

        sections = (
            self._section("summary", SectionType.SUMMARY, snapshot.summary, 10),
            self._section("positions", SectionType.PORTFOLIO, snapshot.positions, 20),
            self._section("dashboard", SectionType.PORTFOLIO, snapshot.dashboard, 30),
            self._section("visualization", SectionType.PORTFOLIO, snapshot.visualization, 40),
            self._status_section(snapshot),
        )

        return PortfolioV2ViewModel(
            title_key="portfolio.workspace.title",
            subtitle_key="portfolio.workspace.subtitle",
            sections=sections,
        )

    def _status_section(self, snapshot) -> BaseSection:
        summary = snapshot.summary[0].values if snapshot.summary else {}
        settings = self._settings
        moex = MoexIndexServiceV1().load()
        return BaseSection(
            section_id="portfolio.statusbar",
            section_type=SectionType.ALERTS,
            title_key="portfolio.statusbar.title",
            subtitle_key="portfolio.statusbar.subtitle",
            order=999,
            status_code=UiStatusCode.OK if summary else UiStatusCode.WARNING,
            status_label_key="ui.status.ok" if summary else "ui.status.warning",
            cards=(BaseCard(
                widget_id="portfolio.statusbar.live",
                widget_type=WidgetType.BASE,
                card_type=CardType.KPI,
                title_key="portfolio.statusbar.title",
                subtitle_key="portfolio.statusbar.subtitle",
                status_code=UiStatusCode.OK if summary else UiStatusCode.WARNING,
                status_label_key="ui.status.ok" if summary else "ui.status.warning",
                payload={
                    "values": {
                        "status": "ONLINE" if summary else "NO DATA",
                        "scope": "REAL",
                        "timezone": settings.timezone,
                        "currency": settings.currency if settings.currency == "RUB" else f"{settings.currency} · данные RUB",
                        "broker": settings.broker if settings.broker == "Finam" else f"{settings.broker} · источник Finam",
                        "moex": moex.value if moex.value is not None else "—",
                        "moex_change": moex.change_pct if moex.change_pct is not None else "—",
                        "moex_freshness": moex.freshness,
                        "positions": summary.get("Позиций", 0),
                        "updated_at": summary.get("Время", ""),
                    },
                    "column_keys": {
                        "status": "portfolio.statusbar.status",
                        "scope": "portfolio.statusbar.scope",
                        "timezone": "portfolio.statusbar.timezone",
                        "currency": "portfolio.statusbar.currency",
                        "broker": "portfolio.statusbar.broker",
                        "moex": "portfolio.statusbar.moex",
                        "moex_change": "portfolio.statusbar.moex_change",
                        "moex_freshness": "portfolio.statusbar.moex_freshness",
                        "positions": "portfolio.statusbar.positions",
                        "updated_at": "portfolio.statusbar.updated",
                    },
                },
            ),),
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
        has_negative_pnl = any(
            "p&l" in str(column_name).lower()
            and isinstance(raw_value, Number)
            and raw_value < 0
            for column_name, raw_value in values.items()
        )
        return BaseCard(
            widget_id=self._formatter.card_id(source_view, index),
            widget_type=WidgetType.BASE,
            card_type=CardType.BASE,
            title_key=self._formatter.source_key(source_view),
            subtitle_key="portfolio.card.subtitle",
            tooltip_key="portfolio.card.tooltip",
            status_code=UiStatusCode.WARNING if has_negative_pnl else UiStatusCode.OK,
            status_label_key="ui.status.warning" if has_negative_pnl else "ui.status.ok",
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
